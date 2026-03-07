from __future__ import annotations

import argparse
import json

from doctr import DocumentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo: input -> docling -> tree index -> retrieval")
    parser.add_argument("path", help="Input path (pdf/docx/pptx/image/...)")
    parser.add_argument("--question", default="What are the main risk factors discussed?")
    args = parser.parse_args()

    pipeline = DocumentPipeline()

    inp = pipeline.document_input(args.path)
    print("Input:", inp)

    converted = pipeline.docling_conversion(args.path)
    print("Converted markdown chars:", len(converted.markdown))

    idx = pipeline.build_tree_index(converted=converted)
    payload = idx.to_pageindex_dict(include_empty_nodes=False)
    print("Top-level nodes:", len(payload.get("nodes", [])))

    context = pipeline.retrieve_for_chat(idx, args.question, top_k=6)
    print("\nRetrieved context:")
    print(context)

    with open("docling_index.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("\nSaved: docling_index.json")


if __name__ == "__main__":
    main()

