from __future__ import annotations

from pathlib import Path
from typing import Any

from .docling_adapter import ConvertedDocument, DoclingConverterAdapter
from .indexer import DocumentIndexer
from .markdown import index_markdown_text
from .models import DocumentIndex
from .retrieval import retrieve_context


class DocumentPipeline:
    """
    Stage-based pipeline:
    1) document_input
    2) docling_conversion
    3) build_tree_index
    4) retrieve_for_chat
    """

    def __init__(self, *, indexer: DocumentIndexer | None = None) -> None:
        self.indexer = indexer or DocumentIndexer()

    def document_input(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        return {
            "path": str(p),
            "file_name": p.name,
            "suffix": p.suffix.lower(),
            "size_bytes": p.stat().st_size,
        }

    def docling_conversion(
        self,
        path: str,
        *,
        converter: DoclingConverterAdapter | None = None,
    ) -> ConvertedDocument:
        c = converter or DoclingConverterAdapter()
        return c.convert(path)

    def build_tree_index(
        self,
        *,
        path: str | None = None,
        converted: ConvertedDocument | None = None,
        max_toc_pages: int = 20,
        prefer_toc_hierarchy: bool = False,
        summary_max_chars: int | None = None,
    ) -> DocumentIndex:
        if converted is not None:
            idx = index_markdown_text(converted.markdown, source=converted.source_path)
            idx.metadata = {**(idx.metadata or {}), **converted.metadata, "index_source": "docling_markdown"}
            return idx
        if path is None:
            raise ValueError("Provide either `path` or `converted`")
        return self.indexer.index_document(
            path,
            max_toc_pages=max_toc_pages,
            prefer_toc_hierarchy=prefer_toc_hierarchy,
            summary_max_chars=summary_max_chars,
        )

    def retrieve_for_chat(self, index: DocumentIndex, question: str, *, top_k: int = 6) -> str:
        payload = index.to_pageindex_dict(include_empty_nodes=False)
        return retrieve_context(payload, question, top_k=top_k)

