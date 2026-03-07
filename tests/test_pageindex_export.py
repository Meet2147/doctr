from doctr import index_markdown_text


def test_pageindex_export_has_node_ids_and_indices() -> None:
    idx = index_markdown_text("# Root\n## Child\n")
    idx.nodes[0].start_page = 1
    idx.nodes[0].end_page = 3
    idx.nodes[0].children[0].start_page = 2
    idx.nodes[0].children[0].end_page = 2

    payload = idx.to_pageindex_dict()
    root = payload["nodes"][0]
    child = root["nodes"][0]

    assert root["node_id"] == "0001"
    assert child["node_id"] == "0002"
    assert root["start_index"] == 1
    assert root["end_index"] == 3
    assert "metadata" in payload
