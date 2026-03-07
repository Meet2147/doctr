<div align="center">
  <img src="https://raw.githubusercontent.com/Meet2147/doctr/main/assets/doctr-logo.png" alt="doctr logo" width="560" />
  <h1>doctr</h1>
  <p>Deterministic multi-format document tree indexing for RAG and agent workflows.</p>

  <p>
    <a href="https://pypi.org/project/doctr-index/"><img alt="PyPI" src="https://img.shields.io/pypi/v/doctr-index"></a>
    <a href="https://pypi.org/project/doctr-index/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/doctr-index"></a>
    <a href="https://github.com/Meet2147/doctr/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/Meet2147/doctr"></a>
  </p>
</div>

## Overview
`doctr` turns real-world documents into PageIndex-style tree nodes:
- `title`
- `node_id`
- `start_index`
- `end_index`
- `summary`
- `nodes`

Supported input formats:
- `pdf`
- `docx`
- `xlsx` / `xlsm`
- `md` / `markdown`
- `txt`
- `msg` (text fallback)
- embedded files inside supported containers (best effort)

## Package Names
- PyPI distribution: `doctr-index`
- Python import: `doctr`
- Legacy compatibility import: `pdfindexing` (shim)

## Installation
```bash
pip install doctr-index
```

Optional extras:
```bash
pip install 'doctr-index[office]'   # docx/xlsx
pip install 'doctr-index[docling]'  # docling adapter
pip install 'doctr-index[ocr]'      # OCR provider adapter
```

## Quick Start
```python
from doctr import index_document

idx = index_document(
    "/path/to/report.pdf",
    prefer_toc_hierarchy=True,
    include_embedded=True,
    max_embedded_depth=2,
)

tree = idx.to_pageindex_dict(include_empty_nodes=False)
print(tree["nodes"][0])
```

## 4-Stage Pipeline
```python
from doctr import DocumentPipeline

pipeline = DocumentPipeline()

# 1) Document input
info = pipeline.document_input("/path/to/report.pdf")

# 2) Docling conversion
converted = pipeline.docling_conversion("/path/to/report.pdf")

# 3) Tree index builder
index = pipeline.build_tree_index(converted=converted)

# 4) Retrieval/chat context
context = pipeline.retrieve_for_chat(index, "What are the key risks?", top_k=6)
print(context)
```

## API Usage Reference

### Core indexing
```python
from doctr import (
    index_document,
    index_pdf_file,
    index_docx_file,
    index_xlsx_file,
    index_markdown_file,
    index_markdown_text,
)

idx1 = index_document("/path/to/file.pdf")
idx2 = index_pdf_file("/path/to/file.pdf")
idx3 = index_docx_file("/path/to/file.docx")
idx4 = index_xlsx_file("/path/to/file.xlsx")
idx5 = index_markdown_file("/path/to/file.md")
idx6 = index_markdown_text("# Root\n## Child")
```

### Class API
```python
from doctr import DocumentIndexer

indexer = DocumentIndexer()
idx = indexer.index_document("/path/to/file.pdf", include_embedded=True)
```

### OCR payload mapping (no API key required)
```python
from doctr import DocumentIndexer, document_index_from_ocr_payload

payload = {
    "doc_id": "pi-abc123",
    "status": "completed",
    "result": [
        {
            "title": "Financial Stability",
            "page_index": 21,
            "text": "...",
            "nodes": []
        }
    ]
}

idx = DocumentIndexer().index_with_ocr("/path/to/scanned.pdf", ocr_payload=payload)
idx2 = document_index_from_ocr_payload(payload, source="/path/to/scanned.pdf")
```

### OCR provider adapter (API key required)
```python
from doctr import PageIndexOCRProvider, DocumentIndexer

provider = PageIndexOCRProvider(api_key="YOUR_KEY", base_url="https://api.pageindex.ai")
idx = DocumentIndexer(ocr_provider=provider).index_with_ocr("/path/to/scanned.pdf")
```

### Retrieval helper
```python
from doctr import index_document, retrieve_context

idx = index_document("/path/to/report.pdf")
payload = idx.to_pageindex_dict(include_empty_nodes=False)
ctx = retrieve_context(payload, "What changed in supervision?", top_k=8)
print(ctx)
```

### Custom enricher
```python
from doctr import index_document

def enrich(idx):
    for node in idx.nodes:
        if node.summary:
            node.summary = node.summary[:300]
    return idx

idx = index_document("/path/to/file.pdf", enricher=enrich)
```

## CLI
```bash
doctr /path/to/file.pdf \
  --prefer-toc-hierarchy \
  --include-embedded \
  --max-embedded-depth 2 \
  --format pageindex \
  --output output_index.json
```

## Embedded Files
Enable recursive embedded indexing:
```python
from doctr import index_document

idx = index_document("/path/to/container.docx", include_embedded=True, max_embedded_depth=2)
```

Output includes:
- `Embedded Files` branch in tree
- `metadata["embedded_files"]` manifest with indexed/skipped status

## Example Scripts
- `examples/chat_with_document.py`
- `examples/docling_pipeline_demo.py`
- `examples/local_ocr_tree_indexer.py`

## Notes
- Normal indexing is local and does not require API keys.
- OCR provider mode requires credentials only if using remote OCR.
- `nodes: []` means a valid leaf node.

## Development
```bash
pytest -q
```

## License
MIT
