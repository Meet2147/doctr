from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pypdf import PdfReader

from .models import DocumentIndex, SectionNode


_TOC_LINE_PATTERNS = [
    re.compile(r"^(?P<title>.+?)\s+\.{2,}\s+(?P<page>\d+)\s*$"),
    re.compile(r"^(?P<title>.+?)\s+(?P<page>\d+)\s*$"),
]
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:section\s+)?(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-Za-z][^\n]{2,120})$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class TOCEntry:
    title: str
    page: int
    level: int


def _parse_pdf_date(value: str | None) -> str | None:
    if not value:
        return None
    # Common PDF date formats, e.g. D:20260101123045+05'30'
    clean = value.strip()
    if clean.startswith("D:"):
        clean = clean[2:]
    match = re.match(r"^(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", clean)
    if not match:
        return value
    parts = [p for p in match.groups() if p]
    while len(parts) < 6:
        parts.append("01" if len(parts) < 3 else "00")
    try:
        dt = datetime(
            int(parts[0]),
            int(parts[1]),
            int(parts[2]),
            int(parts[3]),
            int(parts[4]),
            int(parts[5]),
        )
        return dt.isoformat()
    except ValueError:
        return value


def _extract_file_metadata(path: str) -> dict[str, Any]:
    stat = os.stat(path)
    return {
        "file_name": os.path.basename(path),
        "file_path": path,
        "file_size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": os.path.splitext(path)[1].lower(),
    }


def _extract_pdf_metadata(reader: PdfReader, pages: list[str], outline_used: bool) -> dict[str, Any]:
    raw = reader.metadata or {}
    text_chars = sum(len(p) for p in pages)
    text_words = sum(len(p.split()) for p in pages if p)
    return {
        "pdf_info": {
            "title": raw.get("/Title"),
            "author": raw.get("/Author"),
            "subject": raw.get("/Subject"),
            "creator": raw.get("/Creator"),
            "producer": raw.get("/Producer"),
            "keywords": raw.get("/Keywords"),
            "creation_date": _parse_pdf_date(raw.get("/CreationDate")),
            "modification_date": _parse_pdf_date(raw.get("/ModDate")),
        },
        "content_stats": {
            "total_pages": len(pages),
            "total_text_chars": text_chars,
            "total_text_words": text_words,
            "average_words_per_page": (text_words / len(pages)) if pages else 0,
        },
        "indexing": {
            "outline_used": outline_used,
            "index_source": "outline" if outline_used else "toc_or_fallback",
        },
    }


def _build_summary_for_range(
    pages: list[str],
    start_page: int | None,
    end_page: int | None,
    max_len: int | None = None,
) -> str | None:
    if start_page is None or start_page < 1 or start_page > len(pages):
        return None
    if end_page is None:
        end_page = start_page
    end_page = max(start_page, min(end_page, len(pages)))

    parts: list[str] = []
    for page_idx in range(start_page - 1, end_page):
        text = pages[page_idx].strip()
        if text:
            parts.append(text)

    if not parts:
        return "[No extractable text in this section]"

    merged = re.sub(r"\s+", " ", " ".join(parts))
    return merged if max_len is None else merged[:max_len]


def _heading_level_from_title(title: str) -> int:
    # Light heuristic: nested numbering implies deeper level (e.g. 2.3.1).
    num_prefix = re.match(r"^\s*(\d+(?:\.\d+)*)", title)
    if num_prefix:
        return len(num_prefix.group(1).split("."))
    indent = len(title) - len(title.lstrip(" "))
    return max(1, indent // 2 + 1)


def _normalize_toc_title(raw: str) -> str:
    title = raw.strip()
    title = re.sub(r"\.{2,}\s*$", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip(" .-")


def _extract_page_from_line(line: str) -> tuple[str, int] | None:
    for idx, pattern in enumerate(_TOC_LINE_PATTERNS):
        match = pattern.match(line)
        if not match:
            continue
        title = _normalize_toc_title(match.group("title"))
        if len(title) < 2:
            return None
        if idx == 1:
            word_count = len(title.split())
            starts_like_heading = bool(re.match(r"^([A-Z0-9]|[IVXLC]+\b)", title))
            if not starts_like_heading or word_count > 14 or len(title) > 100:
                return None
        return (title, int(match.group("page")))
    return None


def _parse_toc_entries(pages: list[str], max_toc_pages: int) -> list[TOCEntry]:
    entries: list[TOCEntry] = []
    seen: set[tuple[str, int]] = set()
    toc_markers = ("table of contents", "contents")
    candidate_indices = [
        idx
        for idx, text in enumerate(pages[:max_toc_pages])
        if any(marker in text.lower() for marker in toc_markers)
    ]
    if not candidate_indices:
        candidate_indices = list(range(min(max_toc_pages, len(pages))))

    # Expand around detected TOC pages.
    expanded: list[int] = []
    for idx in candidate_indices:
        for j in range(idx, min(idx + 4, len(pages), max_toc_pages)):
            expanded.append(j)
    scan_indices = sorted(set(expanded))

    for idx in scan_indices:
        page_text = pages[idx]
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            parsed = _extract_page_from_line(line)
            if not parsed:
                continue
            title, page_num = parsed
            key = (title.lower(), page_num)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                TOCEntry(title=title, page=page_num, level=_heading_level_from_title(title))
            )
    return entries


def _entries_from_page_headings(pages: list[str]) -> list[TOCEntry]:
    entries: list[TOCEntry] = []
    seen: set[tuple[str, int]] = set()
    for page_num, page_text in enumerate(pages, start=1):
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        for line in lines[:60]:
            line = re.sub(r"\s{2,}", " ", line)
            match = _NUMBERED_HEADING_RE.match(line)
            if not match:
                continue
            num = match.group("num")
            heading = f"{num} {match.group('title').strip()}"
            key = (heading.lower(), page_num)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                TOCEntry(
                    title=_normalize_toc_title(heading),
                    page=page_num,
                    level=len(num.split(".")),
                )
            )
            # One strong heading per page is usually enough.
            break
    return _clean_and_validate_entries(entries, len(pages))


def _build_tree(
    entries: list[TOCEntry],
    total_pages: int,
    pages: list[str] | None = None,
    summary_max_chars: int | None = None,
) -> list[SectionNode]:
    roots: list[SectionNode] = []
    stack: list[tuple[int, SectionNode]] = []
    flat_nodes: list[SectionNode] = []

    for entry in entries:
        node = SectionNode(title=entry.title, start_page=entry.page)
        while stack and stack[-1][0] >= entry.level:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((entry.level, node))
        flat_nodes.append(node)

    for idx, node in enumerate(flat_nodes):
        next_page = flat_nodes[idx + 1].start_page if idx + 1 < len(flat_nodes) else total_pages + 1
        if node.start_page is not None and next_page is not None:
            node.end_page = max(node.start_page, next_page - 1)
        if pages is not None:
            node.summary = _build_summary_for_range(
                pages,
                node.start_page,
                node.end_page,
                max_len=summary_max_chars,
            )

    return roots


def _fallback_page_index(pages: list[str], summary_max_chars: int | None = None) -> list[SectionNode]:
    nodes: list[SectionNode] = []
    for i, text in enumerate(pages, start=1):
        first_line = text.splitlines()[0].strip() if text else ""
        title = first_line[:80] if first_line else f"Page {i}"
        nodes.append(
            SectionNode(
                title=title,
                start_page=i,
                end_page=i,
                summary=_build_summary_for_range(pages, i, i, max_len=summary_max_chars),
            )
        )
    return nodes


def _clean_and_validate_entries(entries: list[TOCEntry], total_pages: int) -> list[TOCEntry]:
    valid = [e for e in entries if 1 <= e.page <= total_pages]
    valid.sort(key=lambda x: (x.page, x.level, x.title.lower()))
    return valid


def _flatten_outline(outline: list[Any], reader: PdfReader, level: int = 1) -> list[TOCEntry]:
    entries: list[TOCEntry] = []
    for item in outline:
        if isinstance(item, list):
            entries.extend(_flatten_outline(item, reader, level + 1))
            continue
        title = getattr(item, "title", None)
        if not title:
            continue
        norm_title = _normalize_toc_title(str(title))
        page_index = reader.get_destination_page_number(item)
        inferred_level = _heading_level_from_title(norm_title)
        entries.append(
            TOCEntry(
                title=norm_title,
                page=page_index + 1,
                level=max(level, inferred_level),
            )
        )
    return entries


def _entries_from_pdf_outline(reader: PdfReader, pages: list[str]) -> list[TOCEntry]:
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []
    entries = _flatten_outline(outline, reader)
    return _clean_and_validate_entries(entries, len(pages))


def index_pdf_file(
    path: str,
    *,
    max_toc_pages: int = 20,
    prefer_toc_hierarchy: bool = False,
    summary_max_chars: int | None = None,
) -> DocumentIndex:
    reader = PdfReader(path)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    outline_entries = _entries_from_pdf_outline(reader, pages)
    toc_entries = _clean_and_validate_entries(
        _parse_toc_entries(pages, max_toc_pages=max_toc_pages),
        len(pages),
    )
    heading_entries = _entries_from_page_headings(pages)
    if prefer_toc_hierarchy and toc_entries:
        entries = toc_entries
    else:
        entries = outline_entries or toc_entries or heading_entries
    nodes = (
        _build_tree(
            entries,
            total_pages=len(pages),
            pages=pages,
            summary_max_chars=summary_max_chars,
        )
        if entries
        else _fallback_page_index(pages, summary_max_chars=summary_max_chars)
    )
    title = nodes[0].title if nodes else None
    metadata = _extract_file_metadata(path)
    metadata.update(_extract_pdf_metadata(reader, pages, outline_used=bool(outline_entries)))
    metadata["indexing"]["index_source"] = (
        "toc_lines"
        if (prefer_toc_hierarchy and toc_entries)
        else (
            "outline"
            if outline_entries
            else ("toc_lines" if toc_entries else ("page_headings" if heading_entries else "page_fallback"))
        )
    )
    metadata["indexing"]["max_toc_pages"] = max_toc_pages
    metadata["indexing"]["prefer_toc_hierarchy"] = prefer_toc_hierarchy
    metadata["indexing"]["summary_max_chars"] = summary_max_chars
    metadata["indexing"]["section_count"] = len(entries) if entries else len(nodes)
    return DocumentIndex(title=title, total_pages=len(pages), nodes=nodes, source=path, metadata=metadata)
