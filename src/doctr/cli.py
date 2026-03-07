from __future__ import annotations

import argparse
import json
import os

from .indexer import index_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctr", description="Build a hierarchical index from PDF or Markdown files."
    )
    parser.add_argument("path", help="Input document path (.pdf, .md, .markdown)")
    parser.add_argument("--max-toc-pages", type=int, default=20, help="Pages to scan for TOC lines.")
    parser.add_argument(
        "--prefer-toc-hierarchy",
        action="store_true",
        help="For PDFs, prioritize TOC-line hierarchy over embedded bookmark outline.",
    )
    parser.add_argument(
        "--summary-max-chars",
        type=int,
        default=None,
        help="Max chars per node summary. Default is full section text.",
    )
    parser.add_argument(
        "--include-embedded",
        action="store_true",
        help="Recursively index supported embedded files (best effort).",
    )
    parser.add_argument(
        "--max-embedded-depth",
        type=int,
        default=2,
        help="Maximum recursion depth for embedded-file indexing.",
    )
    parser.add_argument("--output", default=None, help="Output JSON file path.")
    parser.add_argument(
        "--format",
        choices=("default", "pageindex"),
        default="pageindex",
        help="Output format. 'pageindex' uses start_index/end_index/node_id fields.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = index_document(
        args.path,
        max_toc_pages=args.max_toc_pages,
        prefer_toc_hierarchy=args.prefer_toc_hierarchy,
        summary_max_chars=args.summary_max_chars,
        include_embedded=args.include_embedded,
        max_embedded_depth=args.max_embedded_depth,
    )

    payload = result.to_dict() if args.format == "default" else result.to_pageindex_dict()
    output_path = args.output
    if output_path is None:
        stem = os.path.splitext(os.path.basename(args.path))[0]
        output_path = f"{stem}_index.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Index written to: {output_path}")


if __name__ == "__main__":
    main()
