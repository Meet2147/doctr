from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any


@dataclass(slots=True)
class Entry:
    title: str
    start_index: int
    level: int


class LocalOCRTreeIndexer:
    """
    Local OCR + tree indexing from scratch.
    No cloud API, no API keys.
    """

    TOC_DOTTED_RE = re.compile(r"^(?P<title>.+?)\s+\.{2,}\s*(?P<page>\d+)\s*$")
    TOC_SIMPLE_RE = re.compile(r"^(?P<title>[A-Z0-9][^\\n]{2,100}?)\s+(?P<page>\d+)\s*$")
    NUMBERED_HEADING_RE = re.compile(
        r"^(?:section\s+)?(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-Za-z][^\n]{2,120})$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        max_toc_pages: int = 20,
        summary_max_chars: int | None = None,
        ocr_dpi: int = 250,
        min_direct_text_chars: int = 80,
        tesseract_lang: str = "eng",
        tesseract_config: str = "--psm 6",
    ) -> None:
        self.max_toc_pages = max_toc_pages
        self.summary_max_chars = summary_max_chars
        self.ocr_dpi = ocr_dpi
        self.min_direct_text_chars = min_direct_text_chars
        self.tesseract_lang = tesseract_lang
        self.tesseract_config = tesseract_config

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _heading_level(self, title: str) -> int:
        num_prefix = re.match(r"^\s*(\d+(?:\.\d+)*)", title)
        if num_prefix:
            return len(num_prefix.group(1).split("."))
        indent = len(title) - len(title.lstrip(" "))
        return max(1, indent // 2 + 1)

    def _build_summary(self, pages_text: list[str], start: int, end: int) -> str:
        parts = []
        for i in range(start - 1, min(end, len(pages_text))):
            t = pages_text[i].strip()
            if t:
                parts.append(t)
        if not parts:
            return "[No extractable text in this section]"
        merged = self._normalize(" ".join(parts))
        return merged if self.summary_max_chars is None else merged[: self.summary_max_chars]

    def extract_pages_text(self, pdf_path: str) -> tuple[list[str], int]:
        """
        Returns (pages_text, ocr_used_pages_count).
        """
        try:
            import fitz  # pymupdf
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency `pymupdf`. Install with: pip install pymupdf pillow pytesseract"
            ) from exc

        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Missing OCR dependencies. Install with: pip install pillow pytesseract"
            ) from exc

        doc = fitz.open(pdf_path)
        pages: list[str] = []
        ocr_used = 0

        for page in doc:
            direct = (page.get_text("text") or "").strip()
            if len(self._normalize(direct)) >= self.min_direct_text_chars:
                pages.append(direct)
                continue

            pix = page.get_pixmap(dpi=self.ocr_dpi)
            image = Image.open(BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(
                image, lang=self.tesseract_lang, config=self.tesseract_config
            )
            text = ocr_text.strip() if ocr_text.strip() else direct
            pages.append(text)
            ocr_used += 1

        doc.close()
        return pages, ocr_used

    def _parse_toc_entries(self, pages_text: list[str]) -> list[Entry]:
        scan_pages = pages_text[: self.max_toc_pages]
        entries: list[Entry] = []
        seen: set[tuple[str, int]] = set()

        for page_text in scan_pages:
            for raw in page_text.splitlines():
                line = raw.strip()
                dotted = self.TOC_DOTTED_RE.match(line)
                simple = self.TOC_SIMPLE_RE.match(line)
                match = dotted or simple
                if not match:
                    continue
                title = self._normalize(match.group("title")).strip(" .-")
                page_idx = int(match.group("page"))
                if page_idx < 1 or page_idx > len(pages_text):
                    continue
                key = (title.lower(), page_idx)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(Entry(title=title, start_index=page_idx, level=self._heading_level(title)))

        entries.sort(key=lambda x: (x.start_index, x.level, x.title.lower()))
        return entries

    def _parse_heading_entries(self, pages_text: list[str]) -> list[Entry]:
        entries: list[Entry] = []
        seen: set[tuple[str, int]] = set()
        for page_num, page_text in enumerate(pages_text, start=1):
            lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
            for line in lines[:80]:
                line = self._normalize(line)
                m = self.NUMBERED_HEADING_RE.match(line)
                if not m:
                    continue
                num = m.group("num")
                title = f"{num} {m.group('title').strip()}"
                key = (title.lower(), page_num)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(Entry(title=title, start_index=page_num, level=len(num.split("."))))
                break
        entries.sort(key=lambda x: (x.start_index, x.level, x.title.lower()))
        return entries

    def _build_tree_nodes(self, entries: list[Entry], pages_text: list[str]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        stack: list[tuple[int, dict[str, Any]]] = []
        flat: list[dict[str, Any]] = []

        for e in entries:
            node = {
                "title": e.title,
                "start_index": e.start_index,
                "end_index": e.start_index,
                "summary": "",
                "nodes": [],
            }
            while stack and stack[-1][0] >= e.level:
                stack.pop()
            if stack:
                stack[-1][1]["nodes"].append(node)
            else:
                nodes.append(node)
            stack.append((e.level, node))
            flat.append(node)

        for i, node in enumerate(flat):
            next_start = flat[i + 1]["start_index"] if i + 1 < len(flat) else len(pages_text) + 1
            node["end_index"] = max(node["start_index"], next_start - 1)
            node["summary"] = self._build_summary(
                pages_text, node["start_index"], node["end_index"]
            )

        # assign node ids in preorder
        counter = 1

        def assign_ids(xs: list[dict[str, Any]]) -> None:
            nonlocal counter
            for n in xs:
                n["node_id"] = str(counter).zfill(4)
                counter += 1
                assign_ids(n["nodes"])

        assign_ids(nodes)
        return nodes

    def _fallback_page_nodes(self, pages_text: list[str]) -> list[dict[str, Any]]:
        nodes = []
        for i, text in enumerate(pages_text, start=1):
            first = text.splitlines()[0].strip() if text else ""
            title = first[:80] if first else f"Page {i}"
            nodes.append(
                {
                    "title": title,
                    "node_id": str(i).zfill(4),
                    "start_index": i,
                    "end_index": i,
                    "summary": self._build_summary(pages_text, i, i),
                    "nodes": [],
                }
            )
        return nodes

    def index_pdf(self, pdf_path: str) -> dict[str, Any]:
        pages_text, ocr_used = self.extract_pages_text(pdf_path)
        toc_entries = self._parse_toc_entries(pages_text)
        heading_entries = self._parse_heading_entries(pages_text)
        entries = toc_entries or heading_entries
        nodes = self._build_tree_nodes(entries, pages_text) if entries else self._fallback_page_nodes(pages_text)

        metadata = {
            "file_name": os.path.basename(pdf_path),
            "file_path": pdf_path,
            "file_size_bytes": os.path.getsize(pdf_path),
            "indexed_at": datetime.now().isoformat(),
            "total_pages": len(pages_text),
            "ocr_used_pages": ocr_used,
            "index_source": "toc_lines" if toc_entries else ("page_headings" if heading_entries else "page_fallback"),
            "section_count": len(entries) if entries else len(nodes),
        }

        return {
            "doc_id": f"pi-{uuid.uuid4().hex[:12]}",
            "status": "completed",
            "title": nodes[0]["title"] if nodes else None,
            "total_pages": len(pages_text),
            "metadata": metadata,
            "result": nodes,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local OCR tree indexer (no API keys).")
    parser.add_argument("pdf_path", help="Path to input PDF")
    parser.add_argument("--output", default="ocr_index.json", help="Output JSON path")
    parser.add_argument("--max-toc-pages", type=int, default=20)
    parser.add_argument("--summary-max-chars", type=int, default=None)
    parser.add_argument("--ocr-dpi", type=int, default=250)
    args = parser.parse_args()

    indexer = LocalOCRTreeIndexer(
        max_toc_pages=args.max_toc_pages,
        summary_max_chars=args.summary_max_chars,
        ocr_dpi=args.ocr_dpi,
    )
    payload = indexer.index_pdf(args.pdf_path)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Index written to: {args.output}")


if __name__ == "__main__":
    main()

