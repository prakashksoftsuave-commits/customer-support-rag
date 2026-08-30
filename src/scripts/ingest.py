"""Ingest the Nimbus help-center KB into Qdrant under every chunking strategy/profile."""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.rag.config import CHUNK_PROFILES
from src.rag.loader import load_kb_documents
from src.rag.splitting import split_documents
from src.rag.vectorstore import build_vectorstore


def main() -> None:
    documents = load_kb_documents()
    print(f"Loaded {len(documents)} KB articles")

    for profile in CHUNK_PROFILES:
        chunks = split_documents(documents, profile)
        build_vectorstore(chunks, profile.collection)
        print(f"[{profile.name}] chunk_size={profile.chunk_size} overlap={profile.chunk_overlap} "
              f"-> {len(chunks)} chunks in collection '{profile.collection}'")


if __name__ == "__main__":
    main()
