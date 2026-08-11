from src.rag.loader import load_kb_documents

REQUIRED_FIELDS = {"source_file", "article_id", "title", "product_area", "last_updated"}


def test_every_document_has_required_metadata():
    documents = load_kb_documents()
    assert len(documents) == 6
    for doc in documents:
        assert REQUIRED_FIELDS.issubset(doc.metadata.keys())
        assert doc.metadata["source_file"]
        assert doc.metadata["article_id"]


def test_article_ids_are_unique():
    documents = load_kb_documents()
    article_ids = [doc.metadata["article_id"] for doc in documents]
    assert len(article_ids) == len(set(article_ids))
