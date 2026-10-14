"""URL normalisation and link discovery."""

import re
from urllib.parse import urlsplit, urlunsplit

# A root-relative path like /visas/getting-a-visa, not preceded by a word
# character or dot (so the path part of "https://host/..." isn't matched twice).
_PATH_RE = re.compile(r"(?<![\w./])/(?:[A-Za-z0-9_\-]+/)*[A-Za-z0-9_\-]+")


def canonicalize(url: str) -> str:
    """One canonical spelling per page, so the same page is never stored twice.

    Lowercases the scheme and host, forces https, and drops the query string,
    fragment and trailing slash. Government content pages don't depend on
    query strings; the ones that do are search/session URLs we don't want.
    """
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", (parts.hostname or "").lower(), path, "", ""))


def embedded_paths(text: str) -> set[str]:
    """Find root-relative paths anywhere in a page's source, not just in <a> tags.

    SharePoint sites (like Home Affairs) ship their navigation and page content
    as escaped JSON inside the HTML, so a normal link extractor sees almost
    nothing. Callers filter the result through `Source.allows`, which discards
    the noise this broad pattern also picks up.
    """
    return set(_PATH_RE.findall(text.replace("\\/", "/")))
