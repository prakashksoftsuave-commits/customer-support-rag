import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
KB_DIR = ROOT_DIR / "data" / "kb"
# Qdrant server (Docker), so collections/vectors are browsable at localhost:6333/dashboard.
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")


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
    name="recursive_small", strategy="recursive", collection="nimbus_kb_recursive_small",
    chunk_size=280, chunk_overlap=40,
)
RECURSIVE_LARGE = ChunkProfile(
    name="recursive_large", strategy="recursive", collection="nimbus_kb_recursive_large",
    chunk_size=900, chunk_overlap=120,
)

# A structurally different strategy: one chunk per "## " section, so a section's
# troubleshooting table always stays attached to its header and never gets split mid-row.
SECTION_AWARE = ChunkProfile(
    name="section_aware", strategy="section_aware", collection="nimbus_kb_section_aware",
)

CHUNK_PROFILES = [RECURSIVE_SMALL, RECURSIVE_LARGE, SECTION_AWARE]
