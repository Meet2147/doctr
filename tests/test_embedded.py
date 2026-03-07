import zipfile

from doctr.embedded import extract_embedded_files
from doctr.indexer import index_document


def test_index_plain_text_file(tmp_path) -> None:
    f = tmp_path / "note.txt"
    f.write_text("hello embedded world", encoding="utf-8")
    idx = index_document(str(f))
    out = idx.to_pageindex_dict(include_empty_nodes=False)
    assert out["nodes"][0]["summary"] == "hello embedded world"


def test_extract_embedded_from_zip_container(tmp_path) -> None:
    docx_like = tmp_path / "sample.docx"
    with zipfile.ZipFile(docx_like, "w") as zf:
        zf.writestr("word/document.xml", "<w:doc/>")
        zf.writestr("word/embeddings/readme.txt", b"inside")

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    embedded = extract_embedded_files(str(docx_like), str(out_dir))
    assert len(embedded) == 1
    assert embedded[0].name == "readme.txt"

