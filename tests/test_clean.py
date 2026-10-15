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
