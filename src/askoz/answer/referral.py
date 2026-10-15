"""Fixed-template referrals for questions AskOz doesn't cover.

A template, not an LLM: it's instant, free, consistent, and can't drift into
answering a question we have no sources for.
"""

from typing import Any

from askoz.answer.agencies import Agency
from askoz.answer.coverage import coverage_note


def not_covered_text() -> str:
    # Short on purpose: the "where to go" card (or the CLI's "Where to go" line)
    # names the agency and links to it, so the text doesn't repeat it.
    return f"**AskOz can't answer this one yet.** {coverage_note()}"


def nothing_found_text(agency: Agency) -> str:
    return (
        "**AskOz couldn't find official information about this.** "
        f"{coverage_note()} Try rephrasing your question, or find the right service "
        f"through {agency.name}."
    )


def referral_payload(agency: Agency, suggestion: str | None = None) -> dict[str, Any]:
    """What the API sends the browser to render a "where to go" card."""
    return {
        "name": agency.name,
        "covers": agency.covers,
        "links": [{"label": link.label, "url": link.url} for link in agency.links],
        "suggestion": suggestion,
    }
