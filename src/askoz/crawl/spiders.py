"""Scrapy spiders: one for sitemap-driven sites, one for link-following sites.

Both emit `RawPage` items. They only fetch and filter; storage happens in
`askoz.crawl.pipeline`, and HTML cleaning happens later, in ingestion.
"""

import contextlib
import urllib.request
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import scrapy
from protego import Protego
from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from askoz.crawl.sources import Source
from askoz.crawl.urls import canonicalize, embedded_paths
from askoz.logging import get_logger

log = get_logger(__name__)


@dataclass
class RawPage:
    url: str
    source: str
    http_status: int
    content_type: str
    body: bytes
    etag: str | None
    last_modified: str | None
    sitemap_lastmod: datetime | None


def robots_crawl_delay(domain: str, user_agent: str) -> float:
    """Read Crawl-delay from robots.txt.

    Scrapy enforces robots.txt Disallow rules but ignores Crawl-delay, so we
    read it ourselves once, before the crawl starts.
    """
    request = urllib.request.Request(
        f"https://{domain}/robots.txt", headers={"User-Agent": user_agent}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except OSError as exc:
        log.warning("robots_fetch_failed", domain=domain, error=str(exc))
        return 0.0
    return Protego.parse(text).crawl_delay(user_agent) or 0.0


def _header(response: Response, name: str) -> str | None:
    value = response.headers.get(name)
    return value.decode("latin-1") if value else None


def to_raw_page(
    response: Response, source: Source, sitemap_lastmod: datetime | None = None
) -> RawPage | None:
    content_type = (_header(response, "Content-Type") or "").lower()
    url = canonicalize(response.url)
    # Skip non-HTML (PDFs come later) and redirects that left our scope,
    # e.g. to a login page.
    if "text/html" not in content_type or not source.allows(url):
        return None
    return RawPage(
        url=url,
        source=source.name,
        http_status=response.status,
        content_type=content_type,
        body=response.body,
        etag=_header(response, "ETag"),
        last_modified=_header(response, "Last-Modified"),
        sitemap_lastmod=sitemap_lastmod,
    )


def crawl_delay(source: Source, user_agent: str) -> float:
    delay = max(source.min_delay, robots_crawl_delay(source.domain, user_agent))
    log.info("crawl_delay", source=source.name, seconds=delay)
    return delay


class SitemapSourceSpider(SitemapSpider):
    name = "sitemap_source"
    allowed_domains: list[str]
    download_delay: float  # Scrapy reads this per spider

    def __init__(self, source: Source, user_agent: str, **kwargs: Any) -> None:
        assert source.sitemap_url is not None
        super().__init__(**kwargs)
        self.source = source
        self.sitemap_urls = [source.sitemap_url]
        self._lastmod: dict[str, datetime] = {}
        self.allowed_domains = [source.domain]
        self.download_delay = crawl_delay(source, user_agent)

    def sitemap_filter(self, entries: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        for entry in entries:
            url = canonicalize(entry["loc"])
            if not self.source.allows(url):
                continue
            if lastmod := entry.get("lastmod"):
                with contextlib.suppress(ValueError):
                    self._lastmod[url] = datetime.fromisoformat(lastmod)
            yield entry

    def parse(self, response: Response, **kwargs: Any) -> Iterator[RawPage]:
        page = to_raw_page(response, self.source, self._lastmod.get(canonicalize(response.url)))
        if page:
            yield page


class LinkSourceSpider(scrapy.Spider):
    name = "link_source"
    allowed_domains: list[str]
    download_delay: float  # Scrapy reads this per spider

    def __init__(self, source: Source, user_agent: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = source
        self.start_urls = [f"https://{source.domain}{path}" for path in source.start_paths]
        self.allowed_domains = [source.domain]
        self.download_delay = crawl_delay(source, user_agent)

    def parse(self, response: Response, **kwargs: Any) -> Iterator[Any]:
        page = to_raw_page(response, self.source)
        if page is None:
            return
        yield page

        candidates = set(response.css("a::attr(href)").getall()) | embedded_paths(response.text)
        for href in candidates:
            url = canonicalize(response.urljoin(href))
            if self.source.allows(url):
                # Scrapy de-duplicates requests, so revisits are dropped for us.
                yield scrapy.Request(url, callback=self.parse)
