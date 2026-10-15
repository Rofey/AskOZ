import pytest

from askoz.answer.pii import find_identifiers, is_medicare_number, is_tfn

# Checksum-valid numbers made up for testing (not real people's).
VALID_TFN = "123456782"
VALID_MEDICARE = "2123456701"


def test_checksums() -> None:
    assert is_tfn(VALID_TFN)
    assert not is_tfn("123456789")
    assert is_medicare_number(VALID_MEDICARE)
    assert not is_medicare_number("2123456791")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            f"my TFN is {VALID_TFN[:3]} {VALID_TFN[3:6]} {VALID_TFN[6:]}, why no refund?",
            ["tax file number"],
        ),
        (f"medicare card {VALID_MEDICARE} expired", ["Medicare number"]),
        ("passport PA1234567 renewal", ["passport number"]),
    ],
)
def test_finds_identifiers(text: str, expected: list[str]) -> None:
    assert find_identifiers(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "is $45,000 taxed at 15% for 2025-26?",
        "call me on 0412 345 678",
        "how much HECS do I repay on 123456789 dollars",
        "what is the DASP tax rate",
    ],
)
def test_ordinary_numbers_are_not_flagged(text: str) -> None:
    assert find_identifiers(text) == []


def test_identifier_values_are_never_returned() -> None:
    assert VALID_TFN not in "".join(find_identifiers(f"tfn {VALID_TFN}"))
