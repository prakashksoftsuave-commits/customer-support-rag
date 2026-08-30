# Nimbus Help Center Assistant — RAG

A small "ask my documents" app over a 6-article mock help-center KB for a fictional cloud
file-sync product — or over your own uploaded pdf/docx/md/txt files. Ingests documents, retrieves
the right passages with LangChain, and answers strictly from what it retrieved — citing the
source article, or admitting it doesn't know. See `results/results.md` for the full write-up:
eight known-answer questions, a chunking-strategy comparison at Top-3 and Top-5, a
metadata-filtering demo, cited answers, refusals, a documented retrieval failure, and (Week 4)
failure labeling + a measured hybrid-search fix with a before/after hit-rate@3 number.

Covers: document loading (built-in KB or uploaded pdf/docx/md/txt), chunking strategies + chunk
size/overlap, embeddings, vector storage, similarity search with metadata filtering, grounded
generation with forced citations/refusal, hybrid (semantic+keyword) search, cross-encoder
reranking, and retrieval-failure debugging with a measured before/after.

## Stack

- Orchestration: [LangChain](https://python.langchain.com/) (`langchain-core`, `langchain-text-splitters`,
  `langchain-huggingface`, `langchain-groq`) — document loading, chunking, retrieval, and the
  generation chain all go through LangChain's abstractions.
- Embeddings: `sentence-transformers` (`all-MiniLM-L6-v2`) via `langchain-huggingface`, local, no API key.
- Generation: Groq (`llama-3.3-70b-versatile` by default) via `langchain-groq`.
- Vector store: **FAISS** by default — local files under `data/faiss_storage/`, no server, no
  Docker. **Qdrant** is also fully wired up (Docker container, server mode, dashboard at
  `http://localhost:6333/dashboard`) and one env var away — see below.
- Frontend: Streamlit.

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Fill in `GROQ_API_KEY` in `.env`. Everything else has a working default — the app runs against
local FAISS files with no other setup.

### Switching to Qdrant instead of FAISS

Both backends are implemented (`src/rag/vectorstore.py`); which one runs is just an env var,
`VECTOR_BACKEND` in `.env` — `faiss` (default) or `qdrant`. Reasons you might want Qdrant: the
browsable dashboard, or a machine where FAISS isn't the better fit. (This project switched *to*
FAISS specifically because the original dev machine's Windows Application Control Policy blocks
`qdrant-client`'s grpc native extension outright — `chromadb` was tried too and hit the same
wall, since it also hard-depends on grpc. FAISS has no grpc dependency at all. If you're on a
machine without that restriction, `qdrant` works exactly the same way it did before.)

To use Qdrant: set `VECTOR_BACKEND=qdrant` in `.env`, start Docker Desktop, then:

```
docker run -d --name nimbus-qdrant -p 6333:6333 -p 6334:6334 -v "%cd%\data\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

Storage persists in `data/qdrant_storage/` on your machine even if the container is removed. To
start it again later after a reboot: `docker start nimbus-qdrant`. To stop it: `docker stop
nimbus-qdrant`. To wipe all vectors and start fresh: `docker rm -f nimbus-qdrant`, delete the
contents of `data/qdrant_storage/`, then re-run the `docker run` command above. Then re-run
`ingest` (below) — collections are backend-specific, so switching backends means re-indexing.

Open `http://localhost:6333/dashboard` any time to browse collections and points visually.

## Running it

Ingest the KB under all three chunking strategies:

```
.venv\Scripts\python -m src.scripts.ingest
```

Run the experiments (each writes its output into `results/`):

```
.venv\Scripts\python -m src.scripts.compare_chunking_strategies
.venv\Scripts\python -m src.scripts.filter_demo
.venv\Scripts\python -m src.scripts.generation_eval
.venv\Scripts\python -m src.scripts.debug_retrieval
```

Launch the app:

```
.venv\Scripts\streamlit run src/app/streamlit_app.py
```

In the app, switch **Document source** to **My uploaded documents** to ask questions over your
own pdf/docx/md/txt files instead of the built-in KB — upload, click **Ingest uploaded files**,
then ask. Uploaded files have no ground-truth answers, so they're for ad hoc Q&A only; the
hit-rate@3 numbers in `results.md` are measured against the labeled built-in KB.

Run tests:

```
.venv\Scripts\pytest tests/
```

## One thing to know

With the default FAISS backend, only one process should write to a given collection at a time
(e.g. don't run `ingest` while Streamlit has that same collection open) — FAISS is local files,
not a server, so there's no lock coordination between processes. Reads (asking questions) are
fine concurrently. Qdrant mode doesn't have this restriction, since it's a real server.

## What each experiment shows

- **`compare_chunking_strategies.py`** — indexes the same 6 articles under `recursive_small`
  (chunk_size=280/overlap=40), `recursive_large` (900/120), and `section_aware`
  (one chunk per `##` section, tables never split from their header). Reports hit-in-top-3 and
  hit-in-top-5 for each, over the same 8 known-answer questions (3 of them table-based). Full
  analysis, including a case where article-level hit-rate hid a wrong-chunk retrieval, is in
  `results/results.md`.
- **`filter_demo.py`** — runs one ambiguous query with and without a `product_area` metadata
  filter, showing the filter change the top-1 result from one article to another.
- **`generation_eval.py`** — runs 3 answerable questions (2 prose, 1 table-based) through the full
  RAG chain with citations, 3 out-of-corpus questions that must be refused, and 1 deliberately
  ambiguous question to show retrieval spreading across articles.
- **`debug_retrieval.py`** (Week 4) — runs 6 known-to-fail compound questions
  (`data/eval/failing_questions.json`), labels each failure ("wrong document fetched" vs "right
  document, wrong answer"), checks reranking (ruled out — it can't fix a document that was never
  retrieved), then measures hit-rate@3 with hybrid search on vs off. Full breakdown in
  `results/results.md` section 12.

## Layout

```
data/kb/              the 6 help-center articles (YAML frontmatter + markdown), one is a
                       troubleshooting-table reference (error codes)
data/eval/            8 known-answer questions, 1 ambiguous question, 3 out-of-corpus questions,
                       6 known-to-fail compound questions (Week 4)
src/rag/              loader (built-in KB + pdf/docx/md/txt uploads), splitter, embeddings,
                       vector store, RAG chain (LangChain) — hybrid search + reranking live here
src/scripts/          the scripts that produce results/
src/app/              the Streamlit app (built-in KB or your own uploaded documents)
results/              results.md write-up + raw JSON output from each experiment
tests/                loader metadata, chunking invariants, upload-loader edge cases
```
