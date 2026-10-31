from llama_index.core.schema import NodeWithScore, TextNode

from askoz.answer.context import SourcePage, complete_sections, fuse_pages, pages_from_results


def _chunk(url: str, text: str) -> NodeWithScore:
    node = TextNode(id_=f"{url}#{text}", text=text, metadata={"url": url, "title": url})
    return NodeWithScore(node=node, score=1.0)


def test_repeated_boilerplate_does_not_fill_every_page_slot() -> None:
    boilerplate = "Get help with your application. Only some people can help you."
    chunks = [_chunk(f"https://x/visa-{i}", boilerplate) for i in range(5)]
    chunks.append(_chunk("https://x/student-500", "You can work 48 hours a fortnight."))
    pages = pages_from_results([chunks], max_pages=5)
    assert [p.url for p in pages] == ["https://x/visa-0", "https://x/student-500"]


def test_chunks_of_one_page_are_grouped_in_rank_order() -> None:
    chunks = [
        _chunk("https://x/a", "first"),
        _chunk("https://x/b", "other"),
        _chunk("https://x/a", "second"),
    ]
    pages = pages_from_results([chunks])
    assert pages[0].sections == ["first", "second"]


def test_a_page_found_by_several_queries_counts_once() -> None:
    lists = [
        [_chunk("https://x/a", "a1"), _chunk("https://x/b", "b1")],
        [_chunk("https://x/a", "a2"), _chunk("https://x/b", "b1")],
    ]
    pages = pages_from_results(lists)
    assert [p.url for p in pages] == ["https://x/a", "https://x/b"]
    assert pages[0].sections == ["a1", "a2"]


def test_agreement_ranks_first_but_every_querys_top_page_gets_a_slot() -> None:
    crowd = [f"https://x/common-{i}" for i in range(8)]
    # Three queries agree on the same pages; one alone finds the right page.
    lists = [crowd, crowd, crowd, ["https://x/right", *crowd]]
    fused = fuse_pages(lists, slots=5)
    assert fused[0] == "https://x/common-0"
    assert "https://x/right" in fused[:5]


MEDICARE = [
    ("/Link Medicare/", "# Link Medicare"),
    ("/Link Medicare/", "## How to link: there are 3 ways"),
    ("/Link Medicare/How to link/", "### Digital ID"),
    ("/Link Medicare/How to link/", "### Medicare card"),
    ("/Link Medicare/How to link/", "### Linking code"),
]


def test_a_small_section_is_completed_in_page_order() -> None:
    page = SourcePage(url="https://x/m", title="Link Medicare", last_updated=None)
    page.sections = ["### Linking code", "### Digital ID"]  # as search ranked them
    complete_sections([page], {"https://x/m": MEDICARE})
    assert page.sections == ["### Digital ID", "### Medicare card", "### Linking code"]


def test_sections_are_left_alone_when_the_page_would_grow_too_big() -> None:
    chunks = [("/Big/", f"part {i}") for i in range(8)]
    page = SourcePage(url="https://x/big", title="Big", last_updated=None)
    page.sections = ["part 5"]
    complete_sections([page], {"https://x/big": chunks})
    assert page.sections == ["part 5"]


def test_sections_are_left_alone_when_the_index_changed() -> None:
    page = SourcePage(url="https://x/m", title="Link Medicare", last_updated=None)
    page.sections = ["text that is no longer indexed"]
    complete_sections([page], {"https://x/m": MEDICARE})
    assert page.sections == ["text that is no longer indexed"]
