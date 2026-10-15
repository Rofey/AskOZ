"""HTML to clean Markdown.

We keep Markdown rather than plain text because headings carry meaning: the
chunker splits on them, and each chunk remembers which section it came from.
"""

import contextlib
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

import lxml.html
import trafilatura

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


def clean_html(html: bytes, url: str = "") -> CleanPage | None:
    """Return the page's main content as Markdown, or None if it has none."""
    schema_text, schema_title = "", ""
    if urlsplit(url).hostname == "immi.homeaffairs.gov.au":
        schema = home_affairs.page_schema(html.decode("utf-8", errors="replace"))
        if schema and home_affairs.is_form(schema):
            return None  # an online form definition, not information
        if schema:
            schema_text = home_affairs.schema_to_markdown(schema)
            schema_title = str(schema.get("title") or "").strip()

    tree = lxml.html.fromstring(html)  # bytes in, so the page's own charset is honoured
    for xpath in _NOISE_XPATHS:
        for element in tree.xpath(xpath):
            element.drop_tree()  # unlike remove(), keeps any text that follows the element

    # Read title and metadata before extract(), which prunes the tree as it works.
    metadata = trafilatura.extract_metadata(tree)
    title = (
        str(tree.xpath("normalize-space(//h1)"))
        or schema_title
        or (metadata.title if metadata else "")
        or ""
    )
    html_body = trafilatura.extract(
        tree,
        output_format="markdown",
        include_tables=True,
        include_links=False,  # link URLs are noise for embeddings; citations use the page URL
        favor_precision=True,  # when unsure, leave it out: boilerplate hurts more than gaps
    )
    body = "\n\n".join(part for part in (html_body, schema_text) if part)
    if not body or len(body) < MIN_BODY_CHARS or not title:
        return None

    last_updated = None
    if metadata and metadata.date:
        with contextlib.suppress(ValueError):
            last_updated = date.fromisoformat(metadata.date)
    return CleanPage(title=title, text=f"# {title}\n\n{body}", last_updated=last_updated)
