from llama_index.core.schema import NodeWithScore, TextNode

from askoz.answer.context import group_into_pages


def _chunk(url: str, text: str) -> NodeWithScore:
    return NodeWithScore(node=TextNode(text=text, metadata={"url": url, "title": url}), score=1.0)


def test_repeated_boilerplate_does_not_fill_every_page_slot() -> None:
    boilerplate = "Get help with your application. Only some people can help you."
    chunks = [_chunk(f"https://x/visa-{i}", boilerplate) for i in range(5)]
    chunks.append(_chunk("https://x/student-500", "You can work 48 hours a fortnight."))
    pages = group_into_pages(chunks, max_pages=5)
    assert [p.url for p in pages] == ["https://x/visa-0", "https://x/student-500"]


def test_chunks_of_one_page_are_grouped_in_rank_order() -> None:
    chunks = [
        _chunk("https://x/a", "first"),
        _chunk("https://x/b", "other"),
        _chunk("https://x/a", "second"),
    ]
    pages = group_into_pages(chunks)
    assert pages[0].sections == ["first", "second"]
