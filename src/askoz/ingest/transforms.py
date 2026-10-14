"""Custom LlamaIndex transformations.

A transformation is any step in an IngestionPipeline: it takes a list of nodes
and returns a list of nodes. Writing your own is how you fix problems that
the built-in parsers don't know about.
"""

from collections.abc import Sequence
from typing import Any

from llama_index.core.schema import BaseNode, TransformComponent


class MergeSmallSections(TransformComponent):
    """Merge sections shorter than `min_chars` into a neighbouring section.

    MarkdownNodeParser makes one node per heading, so a heading followed
    directly by a subheading becomes a node containing only the heading.
    Such a node embeds close to many queries but holds no answer. Small
    sections are merged forward into the next section of the same page; a
    small last section is merged back into the previous one.
    """

    min_chars: int = 300

    def __call__(self, nodes: Sequence[BaseNode], **kwargs: Any) -> list[BaseNode]:
        merged: list[BaseNode] = []
        pending: BaseNode | None = None  # a small section waiting to be merged forward

        for node in nodes:
            if pending is not None:
                if pending.ref_doc_id == node.ref_doc_id:
                    node.set_content(f"{pending.get_content()}\n\n{node.get_content()}")
                else:
                    self._merge_back(merged, pending)
                pending = None
            if len(node.get_content()) < self.min_chars:
                pending = node
            else:
                merged.append(node)

        if pending is not None:
            self._merge_back(merged, pending)
        return merged

    @staticmethod
    def _merge_back(merged: list[BaseNode], small: BaseNode) -> None:
        previous = merged[-1] if merged else None
        if previous is not None and previous.ref_doc_id == small.ref_doc_id:
            previous.set_content(f"{previous.get_content()}\n\n{small.get_content()}")
        else:
            merged.append(small)  # the page's only section: keep it rather than lose it
