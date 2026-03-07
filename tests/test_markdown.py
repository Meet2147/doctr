from doctr import index_markdown_text


def test_markdown_builds_nested_tree() -> None:
    content = """# Root
Some intro
## Section A
### Section A.1
## Section B
"""
    idx = index_markdown_text(content)
    data = idx.to_dict()

    assert data["title"] == "Root"
    assert len(data["nodes"]) == 1
    root = data["nodes"][0]
    assert root["title"] == "Root"
    assert len(root["nodes"]) == 2
    assert root["nodes"][0]["title"] == "Section A"
    assert root["nodes"][0]["nodes"][0]["title"] == "Section A.1"
    assert "metadata" in data
    assert data["metadata"]["content_stats"]["heading_count"] == 4
