from __future__ import annotations

import os
import re
from datetime import datetime

from .models import DocumentIndex, SectionNode


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def index_markdown_text(markdown: str, *, source: str | None = None) -> DocumentIndex:
    stack: list[tuple[int, SectionNode]] = []
    roots: list[SectionNode] = []
    heading_count = 0

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if not match:
            continue

        heading_count += 1
        level = len(match.group(1))
        title = match.group(2).strip()
        node = SectionNode(title=title)

        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((level, node))

    line_count = len(markdown.splitlines())
    word_count = len(markdown.split())
    metadata = {
        "content_stats": {
            "line_count": line_count,
            "word_count": word_count,
            "heading_count": heading_count,
        },
        "indexing": {"index_source": "markdown_headings"},
    }
    return DocumentIndex(
        title=roots[0].title if roots else None,
        total_pages=None,
        nodes=roots,
        source=source,
        metadata=metadata,
    )


def index_markdown_file(path: str) -> DocumentIndex:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    stat = os.stat(path)
    idx = index_markdown_text(content, source=path)
    idx.metadata = {
        **(idx.metadata or {}),
        "file_name": os.path.basename(path),
        "file_path": path,
        "file_size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": os.path.splitext(path)[1].lower(),
    }
    return idx
