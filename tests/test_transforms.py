from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode

from askoz.ingest.transforms import MergeSmallSections


def _node(text: str, doc: str) -> TextNode:
    node = TextNode(text=text)
    node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=doc)
    return node


def test_small_section_merges_forward_within_page() -> None:
    nodes = [_node("# Title", "a"), _node("## Body " + "x" * 400, "a")]
    out = MergeSmallSections(min_chars=300)(nodes)
    assert len(out) == 1
    assert out[0].get_content().startswith("# Title\n\n## Body")


def test_small_last_section_merges_back_not_across_pages() -> None:
    nodes = [_node("A" * 400, "a"), _node("short tail", "a"), _node("B" * 400, "b")]
    out = MergeSmallSections(min_chars=300)(nodes)
    assert [n.ref_doc_id for n in out] == ["a", "b"]
    assert out[0].get_content().endswith("short tail")


def test_page_with_only_a_small_section_is_kept() -> None:
    out = MergeSmallSections(min_chars=300)([_node("tiny", "a")])
    assert len(out) == 1
