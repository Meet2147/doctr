from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from .embedded import extract_embedded_files
from .enrich import IndexEnricher
from .markdown import index_markdown_file
from .models import DocumentIndex, SectionNode
from .office import index_docx_file, index_xlsx_file
from .pdf import index_pdf_file


class OCRProvider(Protocol):
    def run(self, path: str) -> dict[str, Any]:
        ...


def document_index_from_ocr_payload(
    payload: dict[str, Any], *, source: str | None = None
) -> DocumentIndex:
    nodes_payload = payload.get("result", [])
    if isinstance(nodes_payload, dict):
        nodes_payload = [nodes_payload]
    if not isinstance(nodes_payload, list):
        raise ValueError("OCR payload must include `result` as a list or object")

    def map_node(raw: dict[str, Any]) -> SectionNode:
        start = raw.get("start_index")
        if start is None:
            start = raw.get("page_index")
        end = raw.get("end_index")
        if end is None:
            end = start
        summary = raw.get("summary")
        if summary is None:
            summary = raw.get("text")
        children = [map_node(child) for child in raw.get("nodes", [])]
        return SectionNode(
            title=str(raw.get("title", "")),
            start_page=start,
            end_page=end,
            summary=summary,
            children=children,
        )

    nodes = [map_node(node) for node in nodes_payload if isinstance(node, dict)]
    title = payload.get("title") or (nodes[0].title if nodes else None)
    total_pages = payload.get("total_pages")
    metadata = {
        "ocr": {
            "doc_id": payload.get("doc_id"),
            "status": payload.get("status"),
        },
        "indexing": {"index_source": "ocr_payload"},
    }
    return DocumentIndex(
        title=title,
        total_pages=total_pages,
        nodes=nodes,
        source=source,
        metadata=metadata,
    )


class DocumentIndexer:
    def __init__(self, *, ocr_provider: OCRProvider | None = None) -> None:
        self.ocr_provider = ocr_provider

    def index_document(
        self,
        path: str,
        *,
        max_toc_pages: int = 20,
        prefer_toc_hierarchy: bool = False,
        summary_max_chars: int | None = None,
        include_embedded: bool = False,
        max_embedded_depth: int = 2,
        _depth: int = 0,
        enricher: IndexEnricher | None = None,
    ) -> DocumentIndex:
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            index = index_pdf_file(
                path,
                max_toc_pages=max_toc_pages,
                prefer_toc_hierarchy=prefer_toc_hierarchy,
                summary_max_chars=summary_max_chars,
            )
        elif suffix == ".docx":
            index = index_docx_file(path)
        elif suffix in {".xlsx", ".xlsm"}:
            index = index_xlsx_file(path)
        elif suffix in {".md", ".markdown"}:
            index = index_markdown_file(path)
        elif suffix in {".txt", ".msg"}:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            index = DocumentIndex(
                title=Path(path).name,
                total_pages=1,
                nodes=[SectionNode(title=Path(path).name, start_page=1, end_page=1, summary=txt or "[Empty file]")],
                source=path,
                metadata={"indexing": {"index_source": "plain_text_file"}},
            )
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        if include_embedded and _depth < max_embedded_depth:
            index = self._attach_embedded_indexes(
                index,
                path,
                max_toc_pages=max_toc_pages,
                prefer_toc_hierarchy=prefer_toc_hierarchy,
                summary_max_chars=summary_max_chars,
                max_embedded_depth=max_embedded_depth,
                depth=_depth,
            )
        return enricher(index) if enricher else index

    def index_with_ocr(
        self,
        path: str,
        *,
        ocr_payload: dict[str, Any] | None = None,
        ocr_provider: OCRProvider | None = None,
        enricher: IndexEnricher | None = None,
    ) -> DocumentIndex:
        payload = ocr_payload
        if payload is None:
            provider = ocr_provider or self.ocr_provider
            if provider is None:
                raise ValueError("No OCR payload or OCR provider was supplied")
            payload = provider.run(path)
        index = document_index_from_ocr_payload(payload, source=path)
        return enricher(index) if enricher else index

    def _attach_embedded_indexes(
        self,
        index: DocumentIndex,
        path: str,
        *,
        max_toc_pages: int,
        prefer_toc_hierarchy: bool,
        summary_max_chars: int | None,
        max_embedded_depth: int,
        depth: int,
    ) -> DocumentIndex:
        with TemporaryDirectory(prefix="doctr_embedded_") as td:
            embedded = extract_embedded_files(path, td)
            if not embedded:
                return index

            embedded_nodes: list[SectionNode] = []
            manifest: list[dict[str, Any]] = []
            for e in embedded:
                try:
                    child = self.index_document(
                        e.path,
                        max_toc_pages=max_toc_pages,
                        prefer_toc_hierarchy=prefer_toc_hierarchy,
                        summary_max_chars=summary_max_chars,
                        include_embedded=True,
                        max_embedded_depth=max_embedded_depth,
                        _depth=depth + 1,
                    )
                    embedded_nodes.append(
                        SectionNode(
                            title=f"Embedded: {e.name}",
                            start_page=child.nodes[0].start_page if child.nodes else None,
                            end_page=child.nodes[-1].end_page if child.nodes else None,
                            summary=f"Embedded file indexed from {e.parent_path}",
                            children=child.nodes,
                        )
                    )
                    manifest.append(
                        {
                            "name": e.name,
                            "kind": e.kind,
                            "indexed": True,
                            "source_parent": e.parent_path,
                        }
                    )
                except Exception as exc:
                    manifest.append(
                        {
                            "name": e.name,
                            "kind": e.kind,
                            "indexed": False,
                            "error": str(exc),
                            "source_parent": e.parent_path,
                        }
                    )

            if embedded_nodes:
                index.nodes.append(
                    SectionNode(
                        title="Embedded Files",
                        summary="Recursively indexed embedded files",
                        children=embedded_nodes,
                    )
                )

            index.metadata = {
                **(index.metadata or {}),
                "embedded_files": manifest,
                "embedded_depth": depth + 1,
            }
            return index


def index_document(
    path: str,
    *,
    max_toc_pages: int = 20,
    prefer_toc_hierarchy: bool = False,
    summary_max_chars: int | None = None,
    include_embedded: bool = False,
    max_embedded_depth: int = 2,
    enricher: IndexEnricher | None = None,
) -> DocumentIndex:
    return DocumentIndexer().index_document(
        path,
        max_toc_pages=max_toc_pages,
        prefer_toc_hierarchy=prefer_toc_hierarchy,
        summary_max_chars=summary_max_chars,
        include_embedded=include_embedded,
        max_embedded_depth=max_embedded_depth,
        enricher=enricher,
    )
