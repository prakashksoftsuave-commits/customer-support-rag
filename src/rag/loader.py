from pathlib import Path

import frontmatter
from langchain_core.documents import Document

from src.rag.config import KB_DIR


def load_kb_documents(kb_dir: Path = KB_DIR) -> list[Document]:
    """Load every KB markdown file into a LangChain Document, frontmatter as metadata."""
    documents = []
    for path in sorted(kb_dir.glob("*.md")):
        post = frontmatter.load(path)
        metadata = {
            "source_file": path.name,
            "article_id": post.get("article_id", path.stem),
            "title": post.get("title", path.stem),
            "product_area": post.get("product_area", "general"),
            "last_updated": str(post.get("last_updated", "")),
        }
        documents.append(Document(page_content=post.content, metadata=metadata))
    return documents
