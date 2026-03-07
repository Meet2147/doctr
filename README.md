<div align="center">
  <img src="./assets/doctr-logo.svg" alt="doctr logo" width="560" />
  <h1>doctr</h1>
</div>

Deterministic document indexing library with PageIndex-style tree output:
- `title`
- `node_id`
- `start_index`
- `end_index`
- `summary`
- `nodes`

Works for `pdf`, `docx`, `xlsx/xlsm`, `md/markdown`, `txt`, `msg`, plus optional embedded-file recursion.

## Package Name

Official package/import name is now **`doctr`**.

Compatibility:
- Legacy imports from `pdfindexing` are still supported via shim modules.

## Install

Core:
```bash
pip install -e '.[dev]'
```

With Office (`docx`, `xlsx`, `xlsm`):
```bash
pip install -e '.[office]'
```

With Docling:
```bash
pip install -e '.[docling]'
```

With OCR provider adapter:
```bash
pip install -e '.[ocr]'
```

## Architecture (Separate Methods)

1. Document input (`pdf/docx/xlsx/...`)
2. Docling conversion (layout + OCR + reading order + tables)
3. Tree index builder
4. Retrieval/chat layer

Use `DocumentPipeline` when you want these stages explicitly separated.

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

## Full Public API (Every Export) with Usage

### 1) `index_document(...)`

Single entrypoint for supported local files.

```python
from doctr import index_document

idx = index_document(
    "/path/to/file.pdf",
    max_toc_pages=20,
    prefer_toc_hierarchy=False,
    summary_max_chars=None,   # full summaries
    include_embedded=False,
    max_embedded_depth=2,
)
```

### 2) `index_pdf_file(path, ...)`

PDF-specific indexing.

```python
from doctr import index_pdf_file

idx = index_pdf_file("/path/to/file.pdf", prefer_toc_hierarchy=True)
```

### 3) `index_docx_file(path)`

DOCX indexing from heading styles and paragraph sections.

```python
from doctr import index_docx_file

idx = index_docx_file("/path/to/file.docx")
```

### 4) `index_xlsx_file(path)`

XLSX/XLSM indexing by sheets and row chunks.

```python
from doctr import index_xlsx_file

idx = index_xlsx_file("/path/to/file.xlsx")
```

### 5) `index_markdown_file(path)`

```python
from doctr import index_markdown_file

idx = index_markdown_file("/path/to/file.md")
```

### 6) `index_markdown_text(markdown)`

```python
from doctr import index_markdown_text

idx = index_markdown_text("# Root\n## Child\n")
```

### 7) `DocumentIndexer`

Class API with normal indexing + OCR indexing methods.

```python
from doctr import DocumentIndexer

indexer = DocumentIndexer()
idx = indexer.index_document("/path/to/file.pdf", include_embedded=True)
```

### 8) `DocumentIndexer.index_with_ocr(...)`

Use OCR payload directly or provider.

```python
from doctr import DocumentIndexer

ocr_payload = {
    "doc_id": "pi-abc123",
    "status": "completed",
    "result": [
        {
            "title": "Financial Stability",
            "page_index": 21,
            "text": "Section text...",
            "nodes": []
        }
    ]
}

idx = DocumentIndexer().index_with_ocr("/path/to/scanned.pdf", ocr_payload=ocr_payload)
```

### 9) `document_index_from_ocr_payload(payload, source=...)`

Standalone converter from OCR node payload to `DocumentIndex`.

```python
from doctr import document_index_from_ocr_payload

idx = document_index_from_ocr_payload(ocr_payload, source="/path/to/scanned.pdf")
```

### 10) `PageIndexOCRProvider`

Optional remote OCR adapter.

```python
from doctr import PageIndexOCRProvider, DocumentIndexer

provider = PageIndexOCRProvider(api_key="YOUR_KEY", base_url="https://api.pageindex.ai")
indexer = DocumentIndexer(ocr_provider=provider)
idx = indexer.index_with_ocr("/path/to/scanned.pdf")
```

### 11) `DocumentPipeline`

Stage-based API.

```python
from doctr import DocumentPipeline

pipeline = DocumentPipeline()

# Stage 1
inp = pipeline.document_input("/path/to/report.pdf")

# Stage 2
converted = pipeline.docling_conversion("/path/to/report.pdf")

# Stage 3
idx = pipeline.build_tree_index(converted=converted)

# Stage 4
context = pipeline.retrieve_for_chat(idx, "What are major risks?", top_k=6)
```

### 12) `DoclingConverterAdapter`

Direct Docling conversion wrapper.

```python
from doctr import DoclingConverterAdapter

adapter = DoclingConverterAdapter()
converted = adapter.convert("/path/to/file.pdf")
print(converted.markdown[:200])
```

### 13) `ConvertedDocument`

Return type from `DoclingConverterAdapter.convert`.

```python
from doctr import ConvertedDocument

obj = ConvertedDocument(
    source_path="/tmp/a.pdf",
    markdown="# Parsed document",
    metadata={"converter": "docling"},
)
```

### 14) `retrieve_context(index_payload, question, top_k=6)`

Context retrieval helper for chat prompts.

```python
from doctr import retrieve_context, index_document

idx = index_document("/path/to/file.pdf")
payload = idx.to_pageindex_dict(include_empty_nodes=False)
ctx = retrieve_context(payload, "What changed in monetary policy?", top_k=8)
print(ctx)
```

### 15) `DocumentIndex` model

Primary output object from indexers.

```python
from doctr import index_document

idx = index_document("/path/to/file.pdf")
print(idx.to_dict())
print(idx.to_pageindex_dict(include_empty_nodes=False))
```

### 16) `SectionNode` model

Useful for custom node construction.

```python
from doctr import SectionNode

n = SectionNode(title="Section A", start_page=10, end_page=12, summary="...")
```

### 17) `IndexEnricher` protocol

Type contract for custom post-processing.

```python
from doctr import index_document

def enrich(idx):
    for node in idx.nodes:
        if node.summary:
            node.summary = node.summary[:300]
    return idx

idx = index_document("/path/to/file.pdf", enricher=enrich)
```

## Embedded Files (Files within Files)

Supported best-effort extraction:
- Office embeddings (`*/embeddings/*`) in `docx/xlsx/xlsm/pptx`
- PDF file attachments

Enable it:
```python
from doctr import index_document

idx = index_document(
    "/path/to/container.docx",
    include_embedded=True,
    max_embedded_depth=2,
)
```

Results:
- Adds `Embedded Files` branch in tree
- Writes extraction/index status in `metadata["embedded_files"]`

## CLI

```bash
doctr /path/to/file.pdf \
  --prefer-toc-hierarchy \
  --include-embedded \
  --max-embedded-depth 2 \
  --format pageindex \
  --output output_index.json
```

## Examples

- Chat over index + Sonar: [chat_with_document.py](/Users/meetjethwa/Development/PDFIndexing/examples/chat_with_document.py)
- Local OCR from scratch (no API keys, no `doctr` import): [local_ocr_tree_indexer.py](/Users/meetjethwa/Development/PDFIndexing/examples/local_ocr_tree_indexer.py)
- Docling 4-stage demo: [docling_pipeline_demo.py](/Users/meetjethwa/Development/PDFIndexing/examples/docling_pipeline_demo.py)

## Notes

- Normal indexing is local and does not require API keys.
- OCR provider mode needs provider credentials.
- `nodes: []` on a node means it is a valid leaf node.

## Development

```bash
pytest -q
```

## License

MIT
