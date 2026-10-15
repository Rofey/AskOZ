"""Home Affairs (immi.homeaffairs.gov.au) page-schema extraction.

The site is SharePoint. Many pages, including every visa product page, keep
their content as JSON in a hidden form field (`PageSchemaHiddenField`) that
JavaScript renders in the browser, so the HTML itself holds only navigation.
The JSON varies by page type but follows one pattern: heading-like fields
(`title`, `text`, ...) next to HTML fragments (`block`, `description`, ...),
nested in lists. A single recursive walker turns all of them into Markdown.
"""

import html
import json
import re
from typing import Any

import lxml.html

_SCHEMA_RE = re.compile(r'id="ctl00_PlaceHolderMain_PageSchemaHiddenField_Input"\s+value="([^"]*)"')

# Fields that are headings for the content next to them.
_HEADING_KEYS = (
    "visaSubclassHeading",
    "citizenshipHeading",
    "title",
    "text",
    "heading",
    "itemName",
    "processTitle",
    "notesHeading",
    "withThisVisaHeading",
)
# Headings stored as siblings of the content they introduce, not around it.
_PAIRED_HEADINGS = {"notes": "notesHeading", "withThisVisa": "withThisVisaHeading"}
# Short overview values that only make sense with a label.
_LABELS = {
    "visaStay": "How long you can stay",
    "visaCost": "Cost",
    "visaProcessingTime": "Processing time",
}
# Navigation, layout and behaviour flags, not content.
_SKIP_KEYS = {
    "tabs",
    "toggleData",
    "recommended",
    "hidden",
    "collapsed",
    "id",
    "hasCustomButton",
    "customButtonLink",
    "customButtonText",
    "customButtonlink",
    "sellAllConditions",
    "seeAllConditions",
    "processMap",
    "currentActor",
    "multipleActors",
    "$$hashKey",
}


def page_schema(raw_html: str) -> dict[str, Any] | None:
    match = _SCHEMA_RE.search(raw_html)
    if not match or not match.group(1).strip():
        return None
    try:
        data = json.loads(html.unescape(match.group(1)))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def is_form(schema: dict[str, Any]) -> bool:
    """Online form definitions (form.io-style `components`) hold labels, not information."""
    return "components" in schema


def fragment_to_markdown(fragment: str) -> str:
    """Convert a small HTML fragment to Markdown: paragraphs, lists and sub-headings."""
    if "<" not in fragment:
        return re.sub(r"\s+", " ", fragment).strip()
    root = lxml.html.fragment_fromstring(fragment, create_parent=True)  # wraps in <div>
    lines: list[str] = []
    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):
            continue  # comments and processing instructions carry no visible text
        text = re.sub(r"\s+", " ", el.text_content()).strip()
        if not text:
            continue
        if tag in ("h2", "h3", "h4", "h5"):
            lines.append(f"#### {text}")
        elif tag == "li" and not el.xpath(".//li"):
            lines.append(f"- {text}")
        elif tag in ("p", "td") and not el.xpath("ancestor::li"):
            lines.append(text)
    if not lines:  # bare text with inline tags only
        text = re.sub(r"\s+", " ", root.text_content()).strip()
        return text
    return "\n".join(lines)


def schema_to_markdown(schema: dict[str, Any]) -> str:
    parts: list[str] = []

    def walk(node: Any, depth: int) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, depth)
            return
        if not isinstance(node, dict):
            return
        level = "#" * min(2 + depth, 4)
        heading = next(
            (
                str(node[k]).strip()
                for k in _HEADING_KEYS
                if k not in _PAIRED_HEADINGS.values()
                and isinstance(node.get(k), str)
                and node[k].strip()
            ),
            None,
        )
        if heading:
            parts.append(f"{level} {fragment_to_markdown(heading)}")
        for key, value in node.items():
            if key in _SKIP_KEYS or key in _HEADING_KEYS:
                continue
            if key == "sponsor" and node.get("multipleActors") is False:
                continue  # template leftovers: the site doesn't show this section
            if isinstance(value, str):
                text = fragment_to_markdown(value)
                if not text:
                    continue
                paired = node.get(_PAIRED_HEADINGS.get(key, ""))
                if isinstance(paired, str) and paired.strip():
                    parts.append(f"{level}# {fragment_to_markdown(paired)}")
                if key in _LABELS:
                    parts.append(f"**{_LABELS[key]}:** {text}")
                elif "<" in value or len(text) > 25:
                    # HTML fragments are content however short; bare short
                    # strings are labels and button text ("Apply").
                    parts.append(text)
            else:
                walk(value, depth + 1)

    walk(schema, 0)
    # Repeated blocks (e.g. the same note under two tabs) add nothing.
    seen: set[str] = set()
    unique = [p for p in parts if not (p in seen or seen.add(p))]
    return "\n\n".join(unique)
