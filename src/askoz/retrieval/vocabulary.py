"""Words people use vs words official pages use.

Embedding models barely connect "tax file number" with "TFN", and the ATO's
TFN application pages say "TFN" throughout. Asked with the full name, search
ranked them 35th-76th (Oct 2026), behind tax-return and visa pages; asked
with "TFN", 2nd. A larger local embedding model didn't change that.

So every search query that uses a full name is also run in the pages' own
short form. Add entries here when real questions miss pages for the same
reason (check with `askoz search` that the short form is what the pages use).
"""

import re

# Full name -> the abbreviation official pages use. Only distinctive ones:
# two-letter forms (SG, PR) would match too much other text.
ABBREVIATIONS = {
    "tax file number": "TFN",
    "Australian business number": "ABN",
    "goods and services tax": "GST",
    "business activity statement": "BAS",
    "departing Australia superannuation payment": "DASP",
    "Medicare levy surcharge": "MLS",
    "low income tax offset": "LITO",
    "fringe benefits tax": "FBT",
    "capital gains tax": "CGT",
    "self-managed super fund": "SMSF",
    "Visa Entitlement Verification Online": "VEVO",
    "Electronic Travel Authority": "ETA",
    "Overseas Student Health Cover": "OSHC",
    "Confirmation of Enrolment": "CoE",
    "Tourist Refund Scheme": "TRS",
}
_PATTERNS = [
    (re.compile(rf"\b{re.escape(full)}s?\b", re.IGNORECASE), short)
    for full, short in ABBREVIATIONS.items()
]


def abbreviate(text: str) -> str:
    """`text` with each full name replaced by its official abbreviation."""
    for pattern, short in _PATTERNS:
        text = pattern.sub(short, text)
    return text


def with_abbreviations(queries: list[str]) -> list[str]:
    """The queries plus, after them, their abbreviated forms where different."""
    extra = [short for q in queries if (short := abbreviate(q)) != q]
    return list(dict.fromkeys([*queries, *extra]))
