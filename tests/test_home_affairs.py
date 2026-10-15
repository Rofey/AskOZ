import html
import json

from askoz.ingest.clean import clean_html
from askoz.ingest.sites.home_affairs import fragment_to_markdown, schema_to_markdown

# Shape copied from a real Home Affairs visa page (eVisitor 651), trimmed.
SCHEMA = {
    "visaSubclassHeading": "Subclass 651",
    "title": "eVisitor",
    "multipleActors": False,
    "tabs": {"data": [{"text": "Overview", "hidden": False}]},
    "recommended": {"cards": [{"title": "Visitor visa", "description": "Another visa"}]},
    "applicant": {
        "overview": {
            "processTitle": "Process",
            "notesHeading": "Things to know",
            "notes": "<ul><li>apply from outside Australia</li></ul>",
            "withThisVisaHeading": "With this visa you can",
            "withThisVisa": "<ul><li>visit family or friends</li></ul>",
            "visaStay": "Up to 3 months at a time",
            "visaCost": "Free",
        },
        "eligibility": {
            "criteria": [
                {
                    "title": "Have an eligible passport",
                    "description": "<p>You must hold a passport from one of these countries.</p>",
                }
            ]
        },
    },
    "sponsor": {"overview": {"visaStay": "This is a permanent visa. Template leftover."}},
}


def _page(schema: dict) -> bytes:
    value = html.escape(json.dumps(schema), quote=True)
    return (
        "<html><body><nav>Menu</nav>"
        '<input type="hidden" name="x" id="ctl00_PlaceHolderMain_PageSchemaHiddenField_Input" '
        f'value="{value}"/></body></html>'
    ).encode()


def test_visa_schema_becomes_structured_markdown() -> None:
    text = schema_to_markdown(SCHEMA)
    assert "**Cost:** Free" in text
    assert "**How long you can stay:** Up to 3 months at a time" in text
    assert "Have an eligible passport" in text
    # A paired heading comes before the list it introduces.
    assert text.index("With this visa you can") < text.index("visit family or friends")


def test_skips_navigation_and_hidden_sponsor_section() -> None:
    text = schema_to_markdown(SCHEMA)
    assert "Another visa" not in text  # "recommended" cross-links
    assert "Overview" not in text  # tab labels
    assert "Template leftover" not in text  # sponsor view not shown when multipleActors is false


def test_clean_html_uses_schema_for_home_affairs_only() -> None:
    page = clean_html(_page(SCHEMA), "https://immi.homeaffairs.gov.au/visas/evisitor-651")
    assert page is not None
    assert page.title == "eVisitor"
    assert "**Cost:** Free" in page.text
    assert clean_html(_page(SCHEMA), "https://www.ato.gov.au/x") is None  # other sites: HTML only


def test_online_forms_are_skipped() -> None:
    form = {"components": [{"title": "Privacy and Security", "content": "<p>Read this</p>"}]}
    assert clean_html(_page(form), "https://immi.homeaffairs.gov.au/help-support/form") is None


def test_fragment_to_markdown() -> None:
    assert fragment_to_markdown("<p>Hello <b>there</b></p><ul><li>one</li><li>two</li></ul>") == (
        "Hello there\n- one\n- two"
    )
    assert fragment_to_markdown("plain   text") == "plain text"


def test_fragments_with_comments_dont_crash() -> None:
    assert fragment_to_markdown("<!-- editor note --><p>Real text</p>") == "Real text"
    assert fragment_to_markdown("<p>Before</p><!-- x --><ul><li>item</li></ul>") == (
        "Before\n- item"
    )
