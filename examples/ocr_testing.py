from doctr import DocumentIndexer, PageIndexOCRProvider

ocr = PageIndexOCRProvider(
    api_key="YOUR_PAGEINDEX_API_KEY",
    base_url="https://api.pageindex.ai",
)
indexer = DocumentIndexer(ocr_provider=ocr)

idx = indexer.index_with_ocr("/path/to/scanned.pdf")
tree = idx.to_pageindex_dict(include_empty_nodes=False)
print(tree)
