from doctr import DocumentIndexer, document_index_from_ocr_payload


def test_document_index_from_ocr_payload_maps_tree() -> None:
    payload = {
        "doc_id": "pi-abc123",
        "status": "completed",
        "result": [
            {
                "title": "Financial Stability",
                "node_id": "0006",
                "page_index": 21,
                "text": "Top section text",
                "nodes": [
                    {
                        "title": "Monitoring Financial Vulnerabilities",
                        "node_id": "0007",
                        "page_index": 22,
                        "text": "Child text",
                    }
                ],
            }
        ],
    }

    idx = document_index_from_ocr_payload(payload, source="demo.pdf")
    out = idx.to_pageindex_dict(include_empty_nodes=False)
    root = out["nodes"][0]
    assert root["title"] == "Financial Stability"
    assert root["start_index"] == 21
    assert root["summary"] == "Top section text"
    assert root["nodes"][0]["title"] == "Monitoring Financial Vulnerabilities"
    assert out["metadata"]["ocr"]["doc_id"] == "pi-abc123"


def test_document_indexer_index_with_ocr_payload() -> None:
    payload = {"status": "completed", "result": {"title": "A", "page_index": 1, "text": "x"}}
    idx = DocumentIndexer().index_with_ocr("x.pdf", ocr_payload=payload)
    out = idx.to_pageindex_dict(include_empty_nodes=False)
    assert out["nodes"][0]["title"] == "A"
    assert out["nodes"][0]["start_index"] == 1

