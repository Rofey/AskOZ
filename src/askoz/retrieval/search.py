"""Search the index four ways, so their behaviour can be compared and measured.

vector   embeddings only: matches meaning, misses exact terms (the default)
keyword  Postgres full-text: matches exact terms, misses paraphrases
hybrid   both, merged with Reciprocal Rank Fusion
rerank   hybrid candidates re-scored by a cross-encoder
"""

from functools import cached_property
from typing import Literal, get_args

from llama_index.core import VectorStoreIndex
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

from askoz.index import embed_model, vector_store
from askoz.retrieval.fusion import reciprocal_rank_fusion
from askoz.retrieval.rerank import CrossEncoderRerank

Mode = Literal["vector", "keyword", "hybrid", "rerank"]
MODES: tuple[Mode, ...] = get_args(Mode)

# How many candidates each first-stage search returns. Higher means better
# recall for fusion and reranking, at the cost of reranker time.
CANDIDATES = 20

# bge models were trained with this optional prefix on queries (not documents).
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class Searcher:
    def __init__(self, *, query_instruction: bool = False) -> None:
        self.query_instruction = query_instruction
        index = VectorStoreIndex.from_vector_store(vector_store(), embed_model=embed_model())
        self._vector = index.as_retriever(similarity_top_k=CANDIDATES)
        self._keyword = index.as_retriever(
            vector_store_query_mode="sparse", similarity_top_k=CANDIDATES, sparse_top_k=CANDIDATES
        )

    @cached_property
    def _reranker(self) -> CrossEncoderRerank:
        return CrossEncoderRerank()  # loaded on first use: it's a separate model download

    def _query(self, question: str) -> QueryBundle:
        # The question text stays as-is for keyword search and reranking; only
        # the string we embed gets the instruction prefix.
        prefix = BGE_QUERY_INSTRUCTION if self.query_instruction else ""
        return QueryBundle(query_str=question, custom_embedding_strs=[prefix + question])

    def _retrieve(self, retriever: BaseRetriever, question: str) -> list[NodeWithScore]:
        return retriever.retrieve(self._query(question))

    def search(
        self, question: str, *, mode: Mode = "vector", top_k: int = 5
    ) -> list[NodeWithScore]:
        if mode == "vector":
            return self._retrieve(self._vector, question)[:top_k]
        if mode == "keyword":
            return self._retrieve(self._keyword, question)[:top_k]

        fused = reciprocal_rank_fusion(
            [
                self._retrieve(self._vector, question),
                self._retrieve(self._keyword, question),
            ]
        )
        if mode == "hybrid":
            return fused[:top_k]
        self._reranker.top_n = top_k
        return self._reranker.postprocess_nodes(fused[:CANDIDATES], self._query(question))


# Mode choice is driven by `askoz eval` (see eval/baseline.json). On the first
# golden set, vector beat hybrid: keyword search is weak on this corpus and
# fusing it in added noise. Re-run the eval before changing the default.
#
# Known issues found while comparing modes on real questions:
# - Vocabulary mismatch: "backpackers" vs the ATO's "working holiday makers".
#   No local reranker fixed it; query rewriting (Phase 6) should.
# - Year-versioned pages: myTax 2024/2025/2026 instructions compete with each
#   other. Tag chunks with their tax year and prefer the latest.
# - Chunks per page: answers get the 3 best chunks of each page, so a page's
#   key table can be left out (e.g. DASP rates for "can I get my super back").
#   Tune with answer-level evals.
# - Perspective: with the ATO business section live, employer-facing pages can
#   outrank the personal page for employee questions (5 golden questions lost
#   rank 1, none left the top 5). Answers stayed in the employee's voice except
#   occasional copied phrasing. Fix if needed: planner tags personal/business
#   and retrieval softly prefers the matching section (a preference, not a
#   filter: renting out a room is personal but lives in the business section).
