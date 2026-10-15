"""Turning search results into the documents Claude reads.

Each query is searched separately, the result lists are merged with Reciprocal
Rank Fusion, and chunks are grouped back into their pages. Claude gets one
document per page, so its citations point at pages, which is what the user
is shown.
"""

from dataclasses import dataclass, field

from llama_index.core.schema import NodeWithScore

from askoz.retrieval.fusion import reciprocal_rank_fusion
from askoz.retrieval.search import Searcher

MAX_PAGES = 5
MAX_CHUNKS_PER_PAGE = 3
CANDIDATES_PER_QUERY = 20
# How much the user's own wording counts relative to each rewrite. Measured on
# the golden set with cached rewrites: weights 1-5 were within one question of
# each other at hit@5 (1.0 was best: 0.93 vs 0.84 without rewriting), so we keep
# the simplest setting. Re-measure before changing it.
ORIGINAL_QUERY_WEIGHT = 1.0


@dataclass
class SourcePage:
    url: str
    title: str
    last_updated: str | None
    sections: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.sections)


def ranked_chunks(
    searcher: Searcher, queries: list[str], *, original_weight: float = ORIGINAL_QUERY_WEIGHT
) -> list[NodeWithScore]:
    """Search every query (vector mode, our best per Phase 5) and fuse the lists.

    `queries[0]` must be the user's original question.
    """
    lists = [searcher.search(q, mode="vector", top_k=CANDIDATES_PER_QUERY) for q in queries]
    if len(lists) == 1:
        return lists[0]
    return reciprocal_rank_fusion(lists, weights=[original_weight] + [1.0] * (len(lists) - 1))


def group_into_pages(
    chunks: list[NodeWithScore], *, max_pages: int = MAX_PAGES
) -> list[SourcePage]:
    pages: dict[str, SourcePage] = {}
    for result in chunks:
        meta = result.node.metadata
        url = meta["url"]
        if url not in pages:
            if len(pages) == max_pages:
                continue
            pages[url] = SourcePage(
                url=url, title=meta["title"], last_updated=meta.get("last_updated")
            )
        page = pages[url]
        if len(page.sections) < MAX_CHUNKS_PER_PAGE:
            page.sections.append(result.node.get_content())
    return list(pages.values())
