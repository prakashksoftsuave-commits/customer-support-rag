import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
KB_DIR = ROOT_DIR / "data" / "kb"

# Which vector store backend to use — "faiss" (local files, no server, no grpc — the default,
# since qdrant-client's grpc dependency is blocked by this machine's Application Control Policy)
# or "qdrant" (Docker server, browsable dashboard — switch back to this on a machine without
# that restriction by setting VECTOR_BACKEND=qdrant, no code changes needed).
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "faiss")
FAISS_DIR = os.getenv("FAISS_DIR", str(ROOT_DIR / "data" / "faiss_storage"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# Langfuse tracing — self-hosted locally (see langfuse/docker-compose.yml), not the Langfuse
# cloud. Unlike LangSmith, Langfuse's LangChain integration isn't auto-global: chain.py attaches
# a callback handler to each call itself (see src/rag/tracing.py) whenever this is enabled.
# LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY are read directly by the Langfuse SDK, not exposed here.
LANGFUSE_TRACING_ENABLED = os.getenv("LANGFUSE_TRACING_ENABLED", "false").lower() == "true"
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")


@dataclass(frozen=True)
class ChunkProfile:
    name: str
    strategy: str  # "recursive" (character-based, size/overlap) or "section_aware" (header-based)
    collection: str
    chunk_size: int | None = None
    chunk_overlap: int | None = None


# Two size/overlap variants of a plain recursive character splitter, used to show
# how chunk size & overlap change retrieval on their own (module topic: "Chunk size & overlap").
RECURSIVE_SMALL = ChunkProfile(
    name="recursive_small", strategy="recursive", collection="kb_recursive_small",
    chunk_size=280, chunk_overlap=40,
)
RECURSIVE_LARGE = ChunkProfile(
    name="recursive_large", strategy="recursive", collection="kb_recursive_large",
    chunk_size=900, chunk_overlap=120,
)

# A structurally different strategy: one chunk per "## " section, so a section's
# troubleshooting table always stays attached to its header and never gets split mid-row.
SECTION_AWARE = ChunkProfile(
    name="section_aware", strategy="section_aware", collection="kb_section_aware",
)

CHUNK_PROFILES = [RECURSIVE_SMALL, RECURSIVE_LARGE, SECTION_AWARE]

# Used for arbitrary user-uploaded files (pdf/docx/md/txt) — those don't reliably have
# markdown "##" headers to split on, so section_aware doesn't apply; plain recursive does.
UPLOAD_PROFILE = ChunkProfile(
    name="upload_recursive", strategy="recursive", collection="uploaded_docs",
    chunk_size=500, chunk_overlap=75,
)
