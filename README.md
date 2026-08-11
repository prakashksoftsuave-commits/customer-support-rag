# Nimbus Help Center Assistant — RAG

A small "ask my documents" app over a 6-article mock help-center KB for a fictional cloud
file-sync product. Ingests the articles, retrieves the right passages with LangChain + Qdrant,
and answers strictly from what it retrieved — citing the source article, or admitting it doesn't
know. See `results/results.md` for the full write-up: eight known-answer questions, a
chunking-strategy comparison at Top-3 and Top-5, a metadata-filtering demo, cited answers,
refusals, and a documented retrieval failure.

Covers: document loading, chunking strategies + chunk size/overlap, embeddings, vector storage,
similarity search with metadata filtering, and grounded generation with forced citations/refusal.

## Stack

- Orchestration: [LangChain](https://python.langchain.com/) (`langchain-core`, `langchain-text-splitters`,
  `langchain-huggingface`, `langchain-qdrant`, `langchain-groq`) — document loading, chunking, retrieval,
  and the generation chain all go through LangChain's abstractions.
- Embeddings: `sentence-transformers` (`all-MiniLM-L6-v2`) via `langchain-huggingface`, local, no API key.
- Generation: Groq (`llama-3.3-70b-versatile` by default) via `langchain-groq`.
- Vector store: Qdrant, running as a **Docker container** (server mode, not embedded), via
  `langchain-qdrant`. Browsable at `http://localhost:6333/dashboard`.
- Frontend: Streamlit.

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Fill in `GROQ_API_KEY` in `.env`. The other variables have working defaults.

Start the Qdrant server (Docker Desktop must be running):

```
docker run -d --name nimbus-qdrant -p 6333:6333 -p 6334:6334 -v "%cd%\data\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

Storage persists in `data/qdrant_storage/` on your machine even if the container is removed. To
start it again later after a reboot: `docker start nimbus-qdrant`. To stop it: `docker stop
nimbus-qdrant`. To wipe all vectors and start fresh: `docker rm -f nimbus-qdrant`, delete the
contents of `data/qdrant_storage/`, then re-run the `docker run` command above.

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
```

Launch the app:

```
.venv\Scripts\streamlit run src/app/streamlit_app.py
```

Run tests:

```
.venv\Scripts\pytest tests/
```

## One thing to know

Because Qdrant now runs as its own server container, multiple things (Streamlit, the eval
scripts, the dashboard) can all read/write it at the same time — no more lock errors from running
two things at once. The container just needs to be up (`docker ps` to check) before you run
anything that talks to Qdrant.

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

## Layout

```
data/kb/              the 6 help-center articles (YAML frontmatter + markdown), one is a
                       troubleshooting-table reference (error codes)
data/eval/            the 8 known-answer questions, 1 ambiguous question, 3 out-of-corpus questions
src/rag/              loader, splitter, embeddings, vector store, RAG chain (LangChain)
src/scripts/          the scripts that produce results/
src/app/              the Streamlit app
results/              results.md write-up + raw JSON output from each experiment
tests/                loader metadata and chunking invariants
```
