from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from doctr import index_document
from doctr.retrieval import retrieve_context


def ask_perplexity(*, api_key: str, model: str, question: str, context: str) -> str:
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer with citations to page ranges from context."},
            {
                "role": "user",
                "content": (
                    "You answer questions from indexed document context.\n"
                    "If context is insufficient, say what is missing.\n\n"
                    f"Question:\n{question}\n\n"
                    f"Retrieved context:\n{context}\n"
                ),
            },
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Perplexity API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling Perplexity: {e}") from e

    parsed = json.loads(body)
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError(f"Unexpected Perplexity response: {body}")
    return choices[0]["message"]["content"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with a document using doctr + Perplexity Sonar.")
    parser.add_argument("path", help="Path to PDF or Markdown file")
    parser.add_argument("--model", default="sonar")
    args = parser.parse_args()

    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        raise RuntimeError("Missing PPLX_API_KEY. Export it before running this script.")

    idx = index_document(args.path)
    payload = idx.to_pageindex_dict()

    print("\nDocument indexed. Type questions (or 'exit').\n")
    while True:
        q = input("You> ").strip()
        if not q or q.lower() in {"exit", "quit"}:
            break

        context = retrieve_context(payload, q, top_k=6)
        answer = ask_perplexity(api_key=api_key, model=args.model, question=q, context=context)
        print(f"\nAssistant> {answer}\n")


if __name__ == "__main__":
    main()
