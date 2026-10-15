"""Cross-encoder reranking.

Embedding search is a *bi-encoder*: question and chunk are turned into vectors
separately, then compared. That's fast enough to search 10,000 chunks, but the
model never sees the two texts together.

A *cross-encoder* reads the question and one chunk side by side and scores how
well that chunk answers that question. It's far more accurate, and far too
slow to run on every chunk, so we run it only on the top candidates from the
fast search: retrieve broadly, then rerank precisely.
"""

import os
from collections.abc import Sequence
from typing import Any

from fastembed.rerank.cross_encoder import TextCrossEncoder
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import MetadataMode, NodeWithScore, QueryBundle
from pydantic import PrivateAttr

from askoz.config import get_settings

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"


class CrossEncoderRerank(BaseNodePostprocessor):
    model_name: str = RERANK_MODEL
    top_n: int = 5
    _model: TextCrossEncoder = PrivateAttr()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        self._model = TextCrossEncoder(
            self.model_name, cache_dir=str(get_settings().models_dir.resolve())
        )

    @classmethod
    def class_name(cls) -> str:
        return "CrossEncoderRerank"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        if query_bundle is None or not nodes:
            return nodes[: self.top_n]
        # EMBED mode includes title and section path, so the reranker knows that
        # "15% on the first $45,000" sits under "Working holiday makers".
        texts: Sequence[str] = [n.node.get_content(metadata_mode=MetadataMode.EMBED) for n in nodes]
        scores = list(self._model.rerank(query_bundle.query_str, texts))
        reranked = sorted(zip(nodes, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [NodeWithScore(node=n.node, score=float(s)) for n, s in reranked[: self.top_n]]
