from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from src.rag.config import ChunkProfile

_HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2")], strip_headers=False
)


def _split_recursive(doc: Document, profile: ChunkProfile) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=profile.chunk_size,
        chunk_overlap=profile.chunk_overlap,
        separators=["\n## ", "\n\n", "\n", " ", ""],
    )
    return splitter.split_text(doc.page_content)


def _split_section_aware(doc: Document) -> list[str]:
    """One chunk per '##' section — a section's table always stays with its header."""
    return [section.page_content for section in _HEADER_SPLITTER.split_text(doc.page_content)]


def split_documents(documents: list[Document], profile: ChunkProfile) -> list[Document]:
    """Split documents under one chunking strategy, tagging each chunk with its origin."""
    chunks = []
    for doc in documents:
        if profile.strategy == "recursive":
            pieces = _split_recursive(doc, profile)
        elif profile.strategy == "section_aware":
            pieces = _split_section_aware(doc)
        else:
            raise ValueError(f"Unknown chunking strategy: {profile.strategy}")

        for i, piece in enumerate(pieces):
            chunk_metadata = dict(doc.metadata)
            chunk_metadata["chunk_id"] = f"{doc.metadata['article_id']}::{profile.name}::{i}"
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_profile"] = profile.name
            chunks.append(Document(page_content=piece, metadata=chunk_metadata))
    return chunks
