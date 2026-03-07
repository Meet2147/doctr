from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ConvertedDocument:
    source_path: str
    markdown: str
    metadata: dict[str, Any]


class DoclingConverterAdapter:
    """
    Thin adapter around docling conversion APIs.
    Keeps docling as an optional dependency.
    """

    def __init__(self) -> None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Docling is not installed. Install with: pip install 'doctr[docling]'"
            ) from exc
        self._converter = DocumentConverter()

    def convert(self, path: str) -> ConvertedDocument:
        result = self._converter.convert(path)
        doc = result.document

        markdown = self._export_markdown(doc)
        metadata = {
            "file_name": Path(path).name,
            "file_path": path,
            "converter": "docling",
        }

        if hasattr(result, "pages"):
            try:
                metadata["total_pages"] = len(result.pages)
            except Exception:
                pass

        return ConvertedDocument(source_path=path, markdown=markdown, metadata=metadata)

    @staticmethod
    def _export_markdown(doc: Any) -> str:
        # Keep compatibility with docling versions.
        for method_name in ("export_to_markdown", "to_markdown"):
            method = getattr(doc, method_name, None)
            if callable(method):
                return str(method())
        raise RuntimeError("Could not export markdown from docling document")

