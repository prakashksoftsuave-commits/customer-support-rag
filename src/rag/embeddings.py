from langchain_huggingface import HuggingFaceEmbeddings

from src.rag.config import EMBED_MODEL

_embeddings = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return _embeddings
