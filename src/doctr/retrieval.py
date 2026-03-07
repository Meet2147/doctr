from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FlatNode:
    title: str
    start_index: int | None
    end_index: int | None
    summary: str | None


def flatten_nodes(nodes: list[dict[str, Any]]) -> list[FlatNode]:
    out: list[FlatNode] = []
    for node in nodes:
        out.append(
            FlatNode(
                title=node.get("title", ""),
                start_index=node.get("start_index"),
                end_index=node.get("end_index"),
                summary=node.get("summary"),
            )
        )
        out.extend(flatten_nodes(node.get("nodes", [])))
    return out


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score_node(node: FlatNode, query_terms: set[str]) -> int:
    hay = f"{node.title} {node.summary or ''}"
    return len(tokenize(hay).intersection(query_terms))


def retrieve_context(index_payload: dict[str, Any], question: str, top_k: int = 6) -> str:
    flat = flatten_nodes(index_payload.get("nodes", []))
    q_terms = tokenize(question)
    ranked = sorted(flat, key=lambda n: score_node(n, q_terms), reverse=True)[:top_k]

    lines: list[str] = []
    for n in ranked:
        page_span = f"{n.start_index}-{n.end_index}" if n.start_index else "unknown"
        lines.append(
            f"- Title: {n.title}\n  Pages: {page_span}\n  Summary: {n.summary or 'N/A'}"
        )
    return "\n".join(lines)

