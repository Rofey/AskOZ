"""HTML to clean Markdown.

We keep Markdown rather than plain text because headings carry meaning: the
chunker splits on them, and each chunk remembers which section it came from.
"""

import contextlib
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

import lxml.html
import trafilatura

from askoz.crawl.sources import source_for_url
from askoz.ingest.sites import home_affairs

# Markup that isn't content: empty jump-link anchors (trafilatura drops any
# heading that starts with a link, so these cost us every ATO <h2>) and
# text meant only for screen readers.
_CLASS = "contains(concat(' ', normalize-space(@class), ' '), ' {} ')"
_NOISE_XPATHS = (
    f"//a[{_CLASS.format('anchor')} and not(normalize-space())]",
    "//span[normalize-space() = 'External Link']",
    f"//*[{_CLASS.format('sr-only')} or {_CLASS.format('visually-hidden')}]",
)

# Pages with less body text than this are hubs or link lists, not answers.
MIN_BODY_CHARS = 200


@dataclass(frozen=True)
class CleanPage:
    title: str
    text: str  # Markdown, starting with "# {title}"
    last_updated: date | None


# Sites on the Home Affairs SharePoint platform, which hides content in JSON.
HOME_AFFAIRS_PORTFOLIO_HOSTS = {"immi.homeaffairs.gov.au", "www.abf.gov.au"}

_SOFT_404 = re.compile(r"\b404\b|\bpage not found\b|\bsauce not found\b", re.IGNORECASE)

# Accessibility skip links that sometimes survive extraction as text.
_SKIP_LINK_LINES = {"skip to content", "skip to content or footer", "skip to main content"}


def tidy_markdown(text: str) -> str:
    """Drop whitespace-only lines, empty headings and skip-link text, and
    collapse runs of blank lines. Some page builders leave dozens of each."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.lower() in _SKIP_LINK_LINES or re.fullmatch(r"#+", stripped):
            continue
        if not stripped:
            if lines and lines[-1] == "":
                continue
            line = ""
        lines.append(line)
    return "\n".join(lines).strip()


def clean_html(html: bytes, url: str = "") -> CleanPage | None:
    """Return the page's main content as Markdown, or None if it has none."""
    schema_text, schema_title = "", ""
    if urlsplit(url).hostname in HOME_AFFAIRS_PORTFOLIO_HOSTS:
        raw = html.decode("utf-8", errors="replace")
        schema = home_affairs.page_schema(raw)
        if schema and home_affairs.is_form(schema):
            return None  # an online form definition, not information
        if schema:
            schema_text = home_affairs.schema_to_markdown(schema)
            schema_title = str(schema.get("title") or "").strip()
        if items := home_affairs.page_data(raw):
            item_text = home_affairs.items_to_markdown(items)
            schema_text = "\n\n".join(p for p in (schema_text, item_text) if p)

    tree = lxml.html.fromstring(html)  # bytes in, so the page's own charset is honoured
    for xpath in _NOISE_XPATHS:
        for element in tree.xpath(xpath):
            element.drop_tree()  # unlike remove(), keeps any text that follows the element

    # Read title and metadata before extract(), which prunes the tree as it works.
    # Soft 404s: some sites answer missing pages with HTTP 200 and an error page
    # (the AEC's "404 - Sauce not found"). Never index those as content.
    page_titles = f"{tree.xpath('normalize-space(//title)')} {tree.xpath('normalize-space(//h1)')}"
    if _SOFT_404.search(page_titles):
        return None

    metadata = trafilatura.extract_metadata(tree)
    title = (
        str(tree.xpath("normalize-space(//h1)"))
        or schema_title
        or (metadata.title if metadata else "")
        or ""
    )
    source = source_for_url(url)
    recall = source is not None and source.extraction == "recall"
    html_body = trafilatura.extract(
        tree,
        output_format="markdown",
        include_tables=True,
        include_links=False,  # link URLs are noise for embeddings; citations use the page URL
        # Precision by default: when unsure, leave it out, since boilerplate hurts
        # more than gaps. Some sources need recall (see Source.extraction).
        favor_precision=not recall,
        favor_recall=recall,
    )
    body = tidy_markdown("\n\n".join(part for part in (html_body, schema_text) if part))
    if not body or len(body) < MIN_BODY_CHARS or not title:
        return None

    last_updated = None
    if metadata and metadata.date:
        with contextlib.suppress(ValueError):
            last_updated = date.fromisoformat(metadata.date)
    return CleanPage(title=title, text=f"# {title}\n\n{body}", last_updated=last_updated)
