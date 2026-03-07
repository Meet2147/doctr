from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SectionNode:
    title: str
    start_page: int | None = None
    end_page: int | None = None
    summary: str | None = None
    children: list["SectionNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "summary": self.summary,
            "nodes": [child.to_dict() for child in self.children],
        }


@dataclass(slots=True)
class DocumentIndex:
    title: str | None
    total_pages: int | None
    nodes: list[SectionNode] = field(default_factory=list)
    source: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "total_pages": self.total_pages,
            "source": self.source,
            "metadata": self.metadata or {},
            "nodes": [node.to_dict() for node in self.nodes],
        }

    def to_pageindex_dict(self, *, include_empty_nodes: bool = True) -> dict[str, Any]:
        counter = {"value": 1}

        def serialize_node(node: SectionNode) -> dict[str, Any]:
            node_id = str(counter["value"]).zfill(4)
            counter["value"] += 1
            children = [serialize_node(child) for child in node.children]
            payload = {
                "title": node.title,
                "node_id": node_id,
                "start_index": node.start_page,
                "end_index": node.end_page,
                "summary": node.summary,
            }
            if include_empty_nodes or children:
                payload["nodes"] = children
            return payload

        return {
            "title": self.title,
            "total_pages": self.total_pages,
            "source": self.source,
            "metadata": self.metadata or {},
            "nodes": [serialize_node(node) for node in self.nodes],
        }
