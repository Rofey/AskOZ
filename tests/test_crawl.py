from pathlib import Path

import pytest

from askoz.crawl.sources import SOURCES
from askoz.crawl.urls import canonicalize, embedded_paths
from askoz.storage import LocalBlobStore


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "http://WWW.ATO.gov.au/individuals-and-families/",
            "https://www.ato.gov.au/individuals-and-families",
        ),
        ("https://www.ato.gov.au/a?utm_source=x#section", "https://www.ato.gov.au/a"),
        ("https://www.ato.gov.au", "https://www.ato.gov.au/"),
    ],
)
def test_canonicalize(raw: str, expected: str) -> None:
    assert canonicalize(raw) == expected


def test_embedded_paths_finds_links_inside_escaped_json() -> None:
    # Shape copied from a real Home Affairs SharePoint page.
    html = (
        r"&quot;<a href=\&quot;/visas/getting-a-visa/visa-listing/student-500\&quot;"
        r'"relativefriendlyurl":"/citizenship/become-a-citizen",'
        r'"absolutefriendlyurl":"https://immiauthor.homeaffairs.gov.au/visas/x"'
    )
    paths = embedded_paths(html)
    assert "/visas/getting-a-visa/visa-listing/student-500" in paths
    assert "/citizenship/become-a-citizen" in paths
    # The path of an absolute URL on another host must not leak through as relative.
    assert "/visas/x" not in paths


def test_ato_scope_excludes_archived_years() -> None:
    ato = SOURCES["ato"]
    assert ato.allows(
        "https://www.ato.gov.au/individuals-and-families/tax-file-number/apply-for-a-tfn"
    )
    assert not ato.allows(
        "https://www.ato.gov.au/individuals-and-families/your-tax-return/instructions-2019/x"
    )
    assert not ato.allows("https://www.ato.gov.au/forms-and-instructions/anything")
    assert not ato.allows("https://evil.example/individuals-and-families/x")


def test_home_affairs_scope() -> None:
    ha = SOURCES["home_affairs"]
    assert ha.allows(
        "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500"
    )
    assert not ha.allows("https://immi.homeaffairs.gov.au/visas-and-more")
    assert not ha.allows("https://immi.homeaffairs.gov.au/visas/Documents/form.pdf")


def test_blob_store_round_trip_and_rejects_path_escape(tmp_path: Path) -> None:
    store = LocalBlobStore(tmp_path)
    store.put("raw/a/b.gz", b"hello")
    assert store.exists("raw/a/b.gz")
    assert store.get("raw/a/b.gz") == b"hello"
    with pytest.raises(ValueError):
        store.put("../outside", b"x")


def test_shared_domain_sources_are_told_apart_by_scope() -> None:
    from askoz.crawl.sources import source_for_url

    assert (
        source_for_url("https://www.ato.gov.au/individuals-and-families/tax-file-number")
        == SOURCES["ato"]
    )
    assert (
        source_for_url(
            "https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/registering-for-gst"
        )
        == SOURCES["ato_business"]
    )
    # Out of both scopes: corporate tax, excise, and the newsroom.
    for path in [
        "businesses-and-organisations/corporate-tax-measures-and-assurance/x",
        "businesses-and-organisations/gst-excise-and-indirect-taxes/excise-on-alcohol/x",
        "businesses-and-organisations/small-business-newsroom/x",
        "businesses-and-organisations/income-deductions-and-concessions/small-business-benchmarks/x",
    ]:
        assert source_for_url(f"https://www.ato.gov.au/{path}") is None
