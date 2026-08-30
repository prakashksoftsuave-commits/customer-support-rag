from src.rag.config import RECURSIVE_LARGE, RECURSIVE_SMALL, SECTION_AWARE
from src.rag.loader import load_kb_documents
from src.rag.splitting import split_documents


def test_small_profile_produces_more_chunks_than_large():
    documents = load_kb_documents()
    small_chunks = split_documents(documents, RECURSIVE_SMALL)
    large_chunks = split_documents(documents, RECURSIVE_LARGE)
    assert len(small_chunks) > len(large_chunks)


def test_recursive_chunks_stay_within_profile_size_budget():
    documents = load_kb_documents()
    for profile in (RECURSIVE_SMALL, RECURSIVE_LARGE):
        for chunk in split_documents(documents, profile):
            assert len(chunk.page_content) <= profile.chunk_size + profile.chunk_overlap


def test_section_aware_never_splits_a_table_from_its_header_row():
    documents = load_kb_documents()
    chunks = split_documents(documents, SECTION_AWARE)
    table_chunks = [c for c in chunks if "| Code | Meaning | Common Cause | Recommended Resolution |" in c.page_content]
    assert table_chunks, "expected at least one chunk to contain a full troubleshooting table"
    for chunk in table_chunks:
        assert "NB-" in chunk.page_content
