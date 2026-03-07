from doctr import index_markdown_text
from doctr.indexer import index_document


def test_custom_enricher_can_modify_index(tmp_path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Root\n## A\n", encoding="utf-8")

    def enrich(idx):
        idx.title = "ENRICHED"
        if idx.nodes:
            idx.nodes[0].summary = "generated-by-llm"
        return idx

    result = index_document(str(md), enricher=enrich)
    assert result.title == "ENRICHED"
    assert result.nodes[0].summary == "generated-by-llm"


def test_markdown_text_function_remains_plain() -> None:
    idx = index_markdown_text("# Root")
    assert idx.title == "Root"

