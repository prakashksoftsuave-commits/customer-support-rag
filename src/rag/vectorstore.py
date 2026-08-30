from pathlib import Path

from langchain_core.documents import Document

from src.rag.config import FAISS_DIR, QDRANT_URL, VECTOR_BACKEND
from src.rag.embeddings import get_embeddings

# Qdrant and FAISS imports are lazy (inside the functions below) so that selecting one backend
# never requires the other's package to even import — e.g. VECTOR_BACKEND=faiss (the default)
# never touches qdrant-client, whose grpc dependency is blocked on this machine.


def _faiss_path(collection_name: str) -> Path:
    return Path(FAISS_DIR) / collection_name


def _build_faiss(chunks: list[Document], collection_name: str):
    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy

    # normalize_L2 + COSINE so ranking matches Qdrant's Distance.COSINE (FAISS otherwise
    # defaults to raw, un-normalized Euclidean distance).
    store = FAISS.from_documents(
        chunks, get_embeddings(), distance_strategy=DistanceStrategy.COSINE, normalize_L2=True
    )
    path = _faiss_path(collection_name)
    path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(path))
    return store


def _get_faiss(collection_name: str):
    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy

    path = _faiss_path(collection_name)
    if not path.exists():
        raise FileNotFoundError(f"No FAISS index at {path} — run ingest first.")
    return FAISS.load_local(
        str(path),
        get_embeddings(),
        allow_dangerous_deserialization=True,
        distance_strategy=DistanceStrategy.COSINE,
        normalize_L2=True,
    )


def _list_faiss_collections() -> list[str]:
    root = Path(FAISS_DIR)
    if not root.exists():
        return []
    return [p.name for p in root.iterdir() if p.is_dir()]


def _build_qdrant(chunks: list[Document], collection_name: str):
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams
    from langchain_qdrant import QdrantVectorStore

    client = QdrantClient(url=QDRANT_URL)
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


def _get_qdrant(collection_name: str):
    from qdrant_client import QdrantClient
    from langchain_qdrant import QdrantVectorStore

    return QdrantVectorStore(
        client=QdrantClient(url=QDRANT_URL), collection_name=collection_name, embedding=get_embeddings()
    )


def _list_qdrant_collections() -> list[str]:
    from qdrant_client import QdrantClient

    return [c.name for c in QdrantClient(url=QDRANT_URL).get_collections().collections]


def build_vectorstore(chunks: list[Document], collection_name: str):
    """(Re)create a collection from scratch and populate it with chunks."""
    if VECTOR_BACKEND == "qdrant":
        return _build_qdrant(chunks, collection_name)
    return _build_faiss(chunks, collection_name)


def get_vectorstore(collection_name: str):
    """Open an existing collection for querying."""
    if VECTOR_BACKEND == "qdrant":
        return _get_qdrant(collection_name)
    return _get_faiss(collection_name)


def list_collections() -> list[str]:
    """Names of collections that already have data, under the active backend."""
    if VECTOR_BACKEND == "qdrant":
        return _list_qdrant_collections()
    return _list_faiss_collections()


def product_area_filter(product_area: str):
    """A metadata filter for `product_area`, shaped for whichever backend is active."""
    if VECTOR_BACKEND == "qdrant":
        from qdrant_client.http import models as qmodels

        return qmodels.Filter(
            must=[qmodels.FieldCondition(key="metadata.product_area", match=qmodels.MatchValue(value=product_area))]
        )
    return {"product_area": product_area}
