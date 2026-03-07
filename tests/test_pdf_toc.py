from doctr.pdf import _build_tree, _parse_toc_entries


def test_toc_line_parsing_and_tree_build() -> None:
    pages = [
        "\n".join(
            [
                "Contents",
                "1 Introduction .......... 1",
                "1.1 Scope .......... 2",
                "2 Results .......... 5",
            ]
        ),
        "Body page",
    ]

    entries = _parse_toc_entries(pages, max_toc_pages=1)
    assert len(entries) == 3
    assert entries[0].title == "1 Introduction"
    assert entries[1].level == 2

    nodes = _build_tree(entries, total_pages=8)
    assert len(nodes) == 2
    assert nodes[0].title == "1 Introduction"
    assert nodes[0].children[0].title == "1.1 Scope"
    assert nodes[0].start_page == 1
    assert nodes[0].end_page == 1
    assert nodes[1].start_page == 5
    assert nodes[1].end_page == 8


def test_toc_parser_accepts_non_dotted_lines() -> None:
    pages = [
        "\n".join(
            [
                "Table of Contents",
                "1 Intro 1",
                "2 Methods 4",
            ]
        )
    ]
    entries = _parse_toc_entries(pages, max_toc_pages=1)
    assert [e.title for e in entries] == ["1 Intro", "2 Methods"]
    assert [e.page for e in entries] == [1, 4]
