from __future__ import annotations

"""
Comprehensive usage examples for doctr.

Run individual functions from this file in your own scripts.
Some examples require optional deps:
- office: python-docx, openpyxl
- docling: docling
- ocr: requests (and provider credentials)
"""

from doctr import (
    ConvertedDocument,
    DoclingConverterAdapter,
    DocumentIndexer,
    DocumentPipeline,
    PageIndexOCRProvider,
    SectionNode,
    document_index_from_ocr_payload,
    index_docx_file,
    index_document,
    index_markdown_file,
    index_markdown_text,
    index_pdf_file,
    index_xlsx_file,
    retrieve_context,
)


def example_index_document() -> None:
    idx = index_document(
        "/path/to/report.pdf",
        prefer_toc_hierarchy=True,
        include_embedded=True,
        max_embedded_depth=2,
    )
    print(idx.to_pageindex_dict(include_empty_nodes=False))


def example_index_pdf_file() -> None:
    idx = index_pdf_file("/path/to/report.pdf", prefer_toc_hierarchy=True)
    print(idx.to_dict())


def example_index_docx_file() -> None:
    idx = index_docx_file("/path/to/file.docx")
    print(idx.to_pageindex_dict())


def example_index_xlsx_file() -> None:
    idx = index_xlsx_file("/path/to/file.xlsx")
    print(idx.to_pageindex_dict())


def example_markdown_indexing() -> None:
    idx1 = index_markdown_file("/path/to/file.md")
    idx2 = index_markdown_text("# Root\n## Child")
    print(idx1.to_dict())
    print(idx2.to_dict())


def example_document_indexer_class() -> None:
    indexer = DocumentIndexer()
    idx = indexer.index_document("/path/to/file.pdf", include_embedded=True)
    print(idx.to_pageindex_dict())


def example_custom_enricher() -> None:
    def enricher(index):
        for node in index.nodes:
            if node.summary:
                node.summary = node.summary[:300]
        return index

    idx = index_document("/path/to/file.pdf", enricher=enricher)
    print(idx.to_dict())


def example_ocr_payload_mapping() -> None:
    payload = {
        "doc_id": "pi-demo",
        "status": "completed",
        "result": [
            {
                "title": "Financial Stability",
                "page_index": 21,
                "text": "Section text",
                "nodes": [],
            }
        ],
    }
    idx1 = document_index_from_ocr_payload(payload, source="/path/to/scanned.pdf")
    idx2 = DocumentIndexer().index_with_ocr("/path/to/scanned.pdf", ocr_payload=payload)
    print(idx1.to_pageindex_dict())
    print(idx2.to_pageindex_dict())


def example_ocr_provider() -> None:
    provider = PageIndexOCRProvider(api_key="YOUR_KEY", base_url="https://api.pageindex.ai")
    idx = DocumentIndexer(ocr_provider=provider).index_with_ocr("/path/to/scanned.pdf")
    print(idx.to_pageindex_dict())


def example_pipeline_stages() -> None:
    pipeline = DocumentPipeline()
    info = pipeline.document_input("/path/to/report.pdf")
    print(info)

    converted = pipeline.docling_conversion("/path/to/report.pdf")
    idx = pipeline.build_tree_index(converted=converted)
    context = pipeline.retrieve_for_chat(idx, "What are the key risks?", top_k=6)
    print(context)


def example_docling_adapter_only() -> None:
    adapter = DoclingConverterAdapter()
    converted = adapter.convert("/path/to/report.pdf")
    print(converted.metadata)
    print(converted.markdown[:500])


def example_converted_document_dataclass() -> None:
    converted = ConvertedDocument(
        source_path="/tmp/a.pdf",
        markdown="# Parsed document\n## Section",
        metadata={"converter": "docling"},
    )
    idx = DocumentPipeline().build_tree_index(converted=converted)
    print(idx.to_pageindex_dict())


def example_retrieve_context() -> None:
    idx = index_document("/path/to/report.pdf")
    payload = idx.to_pageindex_dict(include_empty_nodes=False)
    context = retrieve_context(payload, "What changed in supervision?", top_k=8)
    print(context)


def example_section_node_manual() -> None:
    node = SectionNode(title="Manual Node", start_page=10, end_page=12, summary="Manual summary")
    print(node.to_dict())

