from askoz.ingest.clean import clean_html

# Mirrors the ATO's real markup: an empty jump-link anchor at the start of each
# <h2>, and a hidden "External Link" label inside outbound links.
PAGE = b"""<!doctype html><html><head><meta charset="utf-8"><title>WHM | ATO</title></head>
<body>
<header><nav><a href="/">Home</a><h2>Log in to ATO online services</h2></nav></header>
<main><article>
  <h1>Working holiday makers</h1>
  <h2 id="x"><a id="Types" class="anchor"></a>Types of visa subclass</h2>
  <p>You&rsquo;re a working holiday maker (WHM) if you have a visa subclass of 417 or 462.
     You can check your visa status using the
     <a href="https://vevo.example">VEVO system<span>External Link</span></a>.</p>
  <h2 id="y"><a id="Rates" class="anchor"></a>Tax rates</h2>
  <p>Registered WHM employers withhold tax at 15% on the first $45,000 you earn during
     2020&ndash;21 and later income years. Higher rates apply above that threshold.</p>
</article></main>
<footer><p>Copyright Australian Taxation Office</p></footer>
</body></html>"""


def test_keeps_section_headings_and_title() -> None:
    page = clean_html(PAGE)
    assert page is not None
    assert page.title == "Working holiday makers"
    assert page.text.startswith("# Working holiday makers")
    assert "Types of visa subclass" in page.text
    assert "Tax rates" in page.text


def test_removes_boilerplate_and_hidden_labels() -> None:
    page = clean_html(PAGE)
    assert page is not None
    assert "External Link" not in page.text
    assert "Log in to ATO online services" not in page.text
    assert "Copyright" not in page.text


def test_decodes_entities() -> None:
    page = clean_html(PAGE)
    assert page is not None
    assert "You\N{RIGHT SINGLE QUOTATION MARK}re" in page.text
    assert "2020\N{EN DASH}21" in page.text


def test_page_without_real_content_is_skipped() -> None:
    hub = b"<html><body><h1>Topics</h1><ul><li><a href='/a'>A</a></li></ul></body></html>"
    assert clean_html(hub) is None


def test_tidy_markdown_removes_layout_debris() -> None:
    from askoz.ingest.clean import tidy_markdown

    messy = (
        "# Title\n\nSkip to content or footer\n\n   \n\t\n\n##  \n\n### \n\nReal text\n\n\n\nMore"
    )
    assert tidy_markdown(messy) == "# Title\n\nReal text\n\nMore"


def test_soft_404_pages_are_not_indexed() -> None:
    page = (
        b"<html><head><title>404 - Sauce not found - Australian Electoral Commission</title>"
        b"</head><body><h1>404 - Sauce not found</h1><p>"
        + b"Don't worry, we're off to the shops to get more. " * 10
        + b"</p></body></html>"
    )
    assert clean_html(page, "https://www.aec.gov.au/update/") is None


def test_case_insensitive_sites_get_one_url_per_page() -> None:
    from askoz.crawl.sources import SOURCES

    aec = SOURCES["aec"]
    assert aec.canonical("https://www.aec.gov.au/Voting/ways_to_vote/") == aec.canonical(
        "https://www.aec.gov.au/voting/Ways_To_Vote"
    )
    assert aec.allows(aec.canonical("https://www.aec.gov.au/Enrolling_to_vote/Special_Category/"))
    assert not aec.allows(aec.canonical("https://www.aec.gov.au/Parties_and_Representatives/x"))
