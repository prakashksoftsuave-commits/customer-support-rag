import io

from docx import Document as DocxDocument

from src.rag.loader import load_uploaded_document, load_uploaded_documents


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(buf)
    return buf.getvalue()


def test_docx_extraction_and_metadata():
    data = _make_docx_bytes(["Hello from a test docx.", "Second paragraph."])
    doc = load_uploaded_document("sample.docx", data)
    assert "Hello from a test docx." in doc.page_content
    assert doc.metadata["article_id"] == "sample"
    assert doc.metadata["product_area"] == "uploaded"


def test_txt_extraction():
    doc = load_uploaded_document("notes.txt", b"plain text content")
    assert doc.page_content == "plain text content"


def test_md_strips_frontmatter():
    md = b"---\ntitle: X\n---\nBody text only.\n"
    doc = load_uploaded_document("notes.md", md)
    assert doc.page_content.strip() == "Body text only."


def test_unsupported_extension_raises():
    try:
        load_uploaded_document("bad.xyz", b"data")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_empty_text_raises():
    try:
        load_uploaded_document("empty.txt", b"   ")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_batch_reports_per_file_failures():
    good = _make_docx_bytes(["Some content."])
    documents, failures = load_uploaded_documents([
        ("good.docx", good),
        ("bad.xyz", b"nope"),
    ])
    assert len(documents) == 1
    assert len(failures) == 1
    assert failures[0][0] == "bad.xyz"
