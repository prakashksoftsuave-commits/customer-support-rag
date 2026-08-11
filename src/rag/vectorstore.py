from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

from src.rag.config import QDRANT_URL
from src.rag.embeddings import get_embeddings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    # Talks to the Qdrant server container over HTTP, so collections/vectors are
    # inspectable in the browser dashboard at QDRANT_URL + "/dashboard".
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def build_vectorstore(chunks: list[Document], collection_name: str) -> QdrantVectorStore:
    """(Re)create a collection from scratch and populate it with chunks."""
    client = get_client()
    embeddings = get_embeddings()

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    dim = len(embeddings.embed_query("dimension probe"))
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    store = QdrantVectorStore(client=client, collection_name=collection_name, embedding=embeddings)
    store.add_documents(chunks)
    return store


def get_vectorstore(collection_name: str) -> QdrantVectorStore:
    """Open an existing collection for querying."""
    return QdrantVectorStore(
        client=get_client(),
        collection_name=collection_name,
        embedding=get_embeddings(),
    )
