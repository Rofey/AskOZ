"""Run a crawl for one source with polite, production-safe Scrapy settings."""

from pathlib import Path
from typing import Any

from scrapy.crawler import CrawlerProcess

from askoz.config import get_settings
from askoz.crawl.sources import SOURCES
from askoz.crawl.spiders import LinkSourceSpider, SitemapSourceSpider


class MissingCrawlContactError(RuntimeError):
    pass


def scrapy_settings(*, limit: int | None, max_depth: int) -> dict[str, Any]:
    settings = get_settings()
    if settings.crawl_contact_url is None:
        raise MissingCrawlContactError(
            "Set ASKOZ_CRAWL_CONTACT_URL in .env to an https:// URL describing the bot. "
            "Sites block crawlers that can't be identified."
        )
    contact = "; ".join(filter(None, [settings.crawl_contact_url, settings.crawl_contact_email]))
    return {
        "BOT_NAME": "askozbot",
        # Identify ourselves honestly so site operators can see who we are and reach us.
        # "Mozilla/5.0 (compatible; Name/version; +contact)" is the standard bot format.
        "USER_AGENT": f"Mozilla/5.0 (compatible; AskOzBot/0.1; +{contact})",
        "ROBOTSTXT_OBEY": True,
        # One request at a time per site. AutoThrottle slows down further if the
        # server gets slower; it never goes below the spider's download_delay.
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_TIMES": 3,
        "DOWNLOAD_TIMEOUT": 30,
        "DOWNLOAD_MAXSIZE": 10 * 1024 * 1024,
        "DEPTH_LIMIT": max_depth,
        # In dev, cache responses on disk so re-running a crawl while we iterate
        # on code doesn't hit government servers again.
        "HTTPCACHE_ENABLED": settings.env == "dev",
        "HTTPCACHE_DIR": str(Path("data/httpcache").resolve()),
        "HTTPCACHE_EXPIRATION_SECS": 7 * 24 * 3600,
        # Never cache blocks, rate limits or server errors, or a retry would just
        # replay the failure from disk instead of asking the server again.
        "HTTPCACHE_IGNORE_HTTP_CODES": [401, 403, 404, 408, 429, 500, 502, 503, 504],
        "ITEM_PIPELINES": {"askoz.crawl.pipeline.RawPagePipeline": 300},
        "CLOSESPIDER_ITEMCOUNT": limit or 0,  # 0 = no limit
        "TELNETCONSOLE_ENABLED": False,
        "LOG_LEVEL": "INFO",
    }


def run_crawl(source_name: str, *, limit: int | None = None) -> None:
    source = SOURCES[source_name]
    settings = scrapy_settings(limit=limit, max_depth=source.max_depth)
    spider_cls = SitemapSourceSpider if source.sitemap_url else LinkSourceSpider
    process = CrawlerProcess(settings)
    process.crawl(spider_cls, source=source, user_agent=settings["USER_AGENT"])
    process.start()
