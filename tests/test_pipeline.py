from doctr import DocumentPipeline
from doctr.docling_adapter import ConvertedDocument


def test_pipeline_document_input(tmp_path) -> None:
    f = tmp_path / "x.md"
    f.write_text("# A", encoding="utf-8")
    p = DocumentPipeline()
    meta = p.document_input(str(f))
    assert meta["file_name"] == "x.md"
    assert meta["suffix"] == ".md"
    assert meta["size_bytes"] > 0


def test_pipeline_build_tree_from_converted() -> None:
    converted = ConvertedDocument(
        source_path="demo.pdf",
        markdown="# Root\n## Child\n",
        metadata={"converter": "docling"},
    )
    p = DocumentPipeline()
    idx = p.build_tree_index(converted=converted)
    out = idx.to_pageindex_dict(include_empty_nodes=False)
    assert out["nodes"][0]["title"] == "Root"
    assert out["nodes"][0]["nodes"][0]["title"] == "Child"


def test_pipeline_retrieve_for_chat() -> None:
    converted = ConvertedDocument(
        source_path="demo.pdf",
        markdown="# Financial Stability\n## Monitoring Financial Vulnerabilities\n",
        metadata={},
    )
    p = DocumentPipeline()
    idx = p.build_tree_index(converted=converted)
    ctx = p.retrieve_for_chat(idx, "financial vulnerabilities", top_k=2)
    assert "Monitoring Financial Vulnerabilities" in ctx

