"""Turning search results into the documents Claude reads.

Each query is searched separately; the result lists are merged per *page*
(Claude gets one document per page, so its citations point at pages, which is
what the user is shown).

How the lists are merged, measured on the golden set over two planner runs
(Oct 2026), against the earlier chunk-level RRF with k=60:

- Page-level RRF. A page's chunks count once, as one page, instead of several
  chunks of one page competing with each other and with other pages.
- k=10, not the textbook 60. With k=60, rank 1 (1/61) is barely better than
  rank 20 (1/80), so middling agreement between lists beat a clear #1 in one.
- Every query's top page gets a slot. When only one query used the page's own
  wording (it says "TFN"; the others said "tax file number" or "visa"), voting
  buried the one right page. Majority agreement is a good default, not a veto.

hit@1 0.58 -> 0.65 and MRR 0.72 -> 0.76 on average; hit@5 unchanged (0.93).
"""

from dataclasses import dataclass, field

from llama_index.core.schema import NodeWithScore

from askoz.retrieval.search import Searcher
from askoz.retrieval.vocabulary import with_abbreviations

MAX_PAGES = 5
MAX_CHUNKS_PER_PAGE = 3
CANDIDATES_PER_QUERY = 20
PAGE_RRF_K = 10


@dataclass
class SourcePage:
    url: str
    title: str
    last_updated: str | None
    sections: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.sections)


def retrieve_pages(
    searcher: Searcher, queries: list[str], *, max_pages: int = MAX_PAGES
) -> list[SourcePage]:
    """Search every query (vector mode, our best per Phase 5) and merge into pages.

    Queries are also run in official short forms ("tax file number" -> "TFN"),
    because that's how the pages themselves are worded (see vocabulary.py).
    """
    lists = [
        searcher.search(q, mode="vector", top_k=CANDIDATES_PER_QUERY)
        for q in with_abbreviations(queries)
    ]
    return pages_from_results(lists, max_pages=max_pages)


def fuse_pages(page_lists: list[list[str]], *, slots: int, k: int = PAGE_RRF_K) -> list[str]:
    """Page URLs best first: reciprocal rank fusion, except that each list's
    top page is guaranteed a place in the first `slots`."""
    scores: dict[str, float] = {}
    for pages in page_lists:
        for rank, url in enumerate(pages, start=1):
            scores[url] = scores.get(url, 0.0) + 1 / (k + rank)
    order = sorted(scores, key=lambda url: scores[url], reverse=True)
    tops = {pages[0] for pages in page_lists if pages}
    chosen = [url for url in order if url in tops][:slots]
    chosen += [url for url in order if url not in chosen][: slots - len(chosen)]
    chosen.sort(key=order.index)
    return chosen + [url for url in order if url not in chosen]


def pages_from_results(
    result_lists: list[list[NodeWithScore]], *, max_pages: int = MAX_PAGES
) -> list[SourcePage]:
    # Each chunk's best rank in any list, so a page's sections come best first.
    best_rank: dict[str, int] = {}
    chunks_by_page: dict[str, dict[str, NodeWithScore]] = {}
    page_lists: list[list[str]] = []
    for results in result_lists:
        pages: list[str] = []
        for rank, result in enumerate(results, start=1):
            node_id, url = result.node.node_id, result.node.metadata["url"]
            best_rank[node_id] = min(rank, best_rank.get(node_id, rank))
            chunks_by_page.setdefault(url, {})[node_id] = result
            if url not in pages:
                pages.append(url)
        page_lists.append(pages)

    out: list[SourcePage] = []
    seen_texts: set[str] = set()
    # Guarantee the top pages a place among the MAX_PAGES Claude reads, even
    # when more are requested (the eval ranks 10), so the eval measures what
    # users get.
    for url in fuse_pages(page_lists, slots=MAX_PAGES):
        if len(out) == max_pages:
            break
        chunks = sorted(chunks_by_page[url].values(), key=lambda c: best_rank[c.node.node_id])
        meta = chunks[0].node.metadata
        page = SourcePage(url=url, title=meta["title"], last_updated=meta.get("last_updated"))
        for chunk in chunks:
            text = chunk.node.get_content()
            # Sites repeat boilerplate across pages (e.g. the same "get help with
            # your application" steps on 40+ visa pages). Take each text once, so
            # five near-identical pages can't fill every slot Claude sees.
            if text in seen_texts or len(page.sections) == MAX_CHUNKS_PER_PAGE:
                continue
            seen_texts.add(text)
            page.sections.append(text)
        if page.sections:
            out.append(page)
    return out
