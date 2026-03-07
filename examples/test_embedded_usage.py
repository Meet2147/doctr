from __future__ import annotations

from pprint import pprint

from doctr import index_document


def run(path: str) -> None:
    idx = index_document(path, include_embedded=True, max_embedded_depth=2)
    payload = idx.to_pageindex_dict(include_empty_nodes=False)
    print(f"\n=== {path} ===")
    embedded = [n for n in payload.get("nodes", []) if n.get("title") == "Embedded Files"]
    print("Embedded branch found:", bool(embedded))
    if embedded:
        print("Embedded children:", len(embedded[0].get("nodes", [])))
    pprint(payload.get("metadata", {}).get("embedded_files", []))


if __name__ == "__main__":
    run("examples/hosts/host_with_embedded.docx")
    run("examples/hosts/host_with_embedded.xlsx")

