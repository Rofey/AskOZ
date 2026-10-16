"""Detect personal identifiers before a question goes anywhere.

AskOz promises not to collect personal information. The web app runs the same
checks as you type (web/src/lib/pii.ts) so identifiers never leave the
browser; this server-side copy is the second layer, for anything that calls
the API directly. Keep the two in step.

Checksums keep false positives (prices, years, reference numbers) low: a
random 9-digit number passes the TFN checksum only 1 time in 11.
"""

import re

_DIGITS = re.compile(r"(?<![\d$])(\d[\d -]{6,13}\d)(?!\d)")
_PASSPORT = re.compile(r"\b[A-Z]{1,2}\d{7}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")
# Australian mobiles (04xx, or +61 4xx) and landlines with an area code (02, 03,
# 07, 08). Not 13/1300/1800 service numbers, which people ask about.
_PHONE = re.compile(r"(?<!\d)(?:\+?61[ -]?\(?|\(?0)[2-478]\)?(?:[ -]?\d){8}(?!\d)")

_TFN_WEIGHTS = {8: (10, 7, 8, 4, 6, 3, 5, 1), 9: (1, 4, 3, 7, 5, 8, 6, 9, 10)}
_MEDICARE_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9)


def is_tfn(digits: str) -> bool:
    weights = _TFN_WEIGHTS.get(len(digits))
    return (
        weights is not None
        and sum(int(d) * w for d, w in zip(digits, weights, strict=True)) % 11 == 0
    )


def is_medicare_number(digits: str) -> bool:
    # 10 digits (11 with the card's individual reference number); first digit 2-6;
    # the 9th digit is a checksum of the first 8.
    if len(digits) not in (10, 11) or digits[0] not in "23456":
        return False
    checksum = sum(int(d) * w for d, w in zip(digits[:8], _MEDICARE_WEIGHTS, strict=True)) % 10
    return checksum == int(digits[8])


def find_identifiers(text: str) -> list[str]:
    """Return the kinds of identifier found (e.g. ["tax file number"]), never the values."""
    found: set[str] = set()
    for match in _DIGITS.finditer(text):
        digits = re.sub(r"[ -]", "", match.group(1))
        if is_tfn(digits):
            found.add("tax file number")
        if is_medicare_number(digits):
            found.add("Medicare number")
    if _PASSPORT.search(text):
        found.add("passport number")
    if _EMAIL.search(text):
        found.add("email address")
    if _PHONE.search(text):
        found.add("phone number")
    return sorted(found)
