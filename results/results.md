# Results — Help Center RAG

A "ask my documents" app over a 6-article mock help-center KB for a fictional cloud
file-sync product. Built with LangChain (text splitters, HuggingFace embeddings, Qdrant vector
store, Groq chat model) over an embedded/local Qdrant index. Every chunk carries
`source_file`, `article_id`, `product_area`, `last_updated` metadata.

Reproduce with:

```
.venv\Scripts\python -m src.scripts.ingest
.venv\Scripts\python -m src.scripts.compare_chunking_strategies
.venv\Scripts\python -m src.scripts.filter_demo
.venv\Scripts\python -m src.scripts.generation_eval
```

Raw output backing every number below is in this folder: `chunking_strategy_comparison.json`,
`filter_demo.json`, `generation_eval.json`.

---

## 1. The knowledge base

| article_id | product_area | title |
|---|---|---|
| kb-account-001 | account | Account Access: Sign-In, Passwords, and Two-Factor Authentication |
| kb-sync-002 | sync | Fixing File Sync and Upload Problems |
| kb-share-003 | sharing | Sharing Files and Managing Permission Roles |
| kb-mobile-004 | mobile | Using the Mobile App: Offline Files and Camera Backup |
| kb-notify-005 | notifications | Notification and Alert Settings |
| kb-errors-006 | general | Error Code Reference (3 troubleshooting tables: sync/upload, account, sharing) |

Every chunk's metadata: `source_file` (filename), `article_id`, `product_area`, `last_updated`,
`title`, plus `chunk_id`/`chunk_index`/`chunk_profile` added at chunking time. A chunk with no
`source_file` is treated as a failed ingest — `tests/test_loader_metadata.py` asserts this for
every article.

## 2. The 8 known-answer questions

| # | Question | Expected article | Table-based? |
|---|---|---|---|
| 1 | How long does a password reset link stay valid before it expires? | kb-account-001 | No |
| 2 | When two devices edit the same file before syncing, what happens to the older version? | kb-sync-002 | No |
| 3 | What is the maximum size allowed for a single file upload? | kb-sync-002 | No |
| 4 | Can someone with the Commenter role edit the actual content of a document? | kb-share-003 | No |
| 5 | If I turn off email notifications for every individual event, does that also stop the weekly digest email? | kb-notify-005 | No |
| 6 | What does error code NB-SYNC-101 mean and how do I fix it? | kb-errors-006 | **Yes** |
| 7 | I got NB-AUTH-410 when using my password reset link — what does that mean? | kb-errors-006 | **Yes** |
| 8 | What should I do about error code NB-SHARE-512? | kb-errors-006 | **Yes** |

Questions were written from the articles first, before any retrieval was run.

## 3. Chunking strategies compared

- **recursive_small** — `RecursiveCharacterTextSplitter`, chunk_size=280, overlap=40.
- **recursive_large** — same splitter, chunk_size=900, overlap=120.
- **section_aware** — `MarkdownHeaderTextSplitter` on `#`/`##`, one chunk per section. A
  section's table always stays attached to its header and is never split mid-row.

All three are indexed from the same 6 articles into separate Qdrant collections.

## 4. Hit-in-Top-3 and Hit-in-Top-5 (article-level)

| Strategy | Hit-in-Top-3 | Hit-in-Top-5 |
|---|---|---|
| recursive_small | 8/8 | 8/8 |
| recursive_large | 8/8 | 8/8 |
| section_aware | 8/8 | 8/8 |

At the article level, all three strategies look identical on this KB: the expected article
appears within Top-3 and Top-5 for all 8 questions. **This number alone is misleading**, which is
exactly what section 5 below found.

## 5. Retrieval failure: article-level hit hides ranking quality

Question 6, "What does error code NB-SYNC-101 mean and how do I fix it?", expects the dedicated
error-reference article, `kb-errors-006`. In the current `recursive_small` Top-5, a semantically
related sync article ranks above that expected article:

| Rank | article_id | chunk_id | score |
|---|---|---|---|
| 1 | kb-sync-002 | kb-sync-002::recursive_small::14 | 0.822 |
| 2 | kb-errors-006 | kb-errors-006::recursive_small::30 | 0.6828 |
| 3 | kb-errors-006 | kb-errors-006::recursive_small::4 | 0.6795 |
| 4 | kb-mobile-004 | kb-mobile-004::recursive_small::15 | 0.6457 |
| 5 | kb-errors-006 | kb-errors-006::recursive_small::21 | 0.5603 |

The correct `kb-errors-006` result is still within the evaluated Top-K at rank 2, so this question
counts as a Hit@3 and Hit@5 in the article-level metric. That is the weakness: article-level
Hit@K can hide chunk/ranking quality issues when the best-ranked chunk is not from the expected
article.

This happens because the query combines an exact error code with broad sync troubleshooting
language: "sync", "mean", and "fix". A sync troubleshooting article can contain dense, semantically
related sync/remediation content that embeds closer to the question than a compact error-reference
chunk, even though `kb-errors-006` is the dedicated source for the code. The expected article is
retrieved, but the ranking still shows why article-level coverage alone is not enough to judge
retrieval quality.

## 6. Metadata filtering: unfiltered vs. filtered

Query: **"Why are my notifications not working?"** — ambiguous between the general notifications
article and the mobile article's push-notification context.

**Unfiltered top-5** (searched across all `product_area` values):

| Rank | article_id | product_area | chunk_id | score |
|---|---|---|---|---|
| 1 | kb-notify-005 | notifications | kb-notify-005::section_aware::4 | 0.6379 |
| 2 | kb-notify-005 | notifications | kb-notify-005::section_aware::2 | 0.5797 |
| 3 | kb-notify-005 | notifications | kb-notify-005::section_aware::7 | 0.5387 |
| 4 | kb-notify-005 | notifications | kb-notify-005::section_aware::0 | 0.5047 |
| 5 | kb-notify-005 | notifications | kb-notify-005::section_aware::6 | 0.5046 |

**Filtered top-5** (`product_area == "mobile"`):

| Rank | article_id | product_area | chunk_id | score |
|---|---|---|---|---|
| 1 | kb-mobile-004 | mobile | kb-mobile-004::section_aware::9 | 0.4371 |
| 2 | kb-mobile-004 | mobile | kb-mobile-004::section_aware::2 | 0.2613 |
| 3 | kb-mobile-004 | mobile | kb-mobile-004::section_aware::7 | 0.2256 |
| 4 | kb-mobile-004 | mobile | kb-mobile-004::section_aware::8 | 0.2159 |
| 5 | kb-mobile-004 | mobile | kb-mobile-004::section_aware::3 | 0.211 |

Top-1 changes from `kb-notify-005` (unfiltered) to `kb-mobile-004` (filtered). The filter forces
mobile-scoped chunks to the top, even though the unfiltered retrieval is dominated by the
notifications article.

## 7. Grounded answers with citations

3 answerable questions run through the full chain (`section_aware`, k=4), each citation checked
against its resolved chunk. Run live against Groq (`openai/gpt-oss-120b`):

1. **Q:** How long does a password reset link stay valid before it expires?
   **A:** Password reset links remain valid for 30 minutes before they expire. [source: kb-account-001::section_aware::6]
   *Verified citation chunk: `kb-account-001::section_aware::6`.*

2. **Q:** Can someone with the Commenter role edit the actual content of a document?
   **A:** No. Commenters can add comments but cannot edit the document's content [ source: kb-share-003::section_aware::6 ].
   *Verified citation chunk: `kb-share-003::section_aware::6`* (model added extra spaces inside the
   brackets here — cosmetic, not corrected, since the citation instruction only asks for the
   `[source: <chunk_id>]` content, not exact whitespace).

3. **Q (table-based):** What does error code NB‑SYNC‑101 mean and how do I fix it?
   **A:** Error `NB‑SYNC‑101` is a known false-positive that can pop up briefly when files are
   edited rapidly; it clears itself automatically and doesn't require any user action to fix.
   [source: kb-errors-006::section_aware::8]
   *Verified citation chunk: `kb-errors-006::section_aware::8`.*

**Regression found and fixed while re-verifying this section live:** the citation instruction and
the `[source: <chunk_id>]` prefix on each context excerpt had been silently dropped from
`SYSTEM_PROMPT`/`format_docs` in `src/rag/chain.py` at some point (visible in git history — present
before the Week 4 hybrid/rerank changes, absent after). Answers were still correct, just no longer
cited anything, which would have failed the "does every answer show which document it came from?"
mentor check. Restored: the citation rule in `SYSTEM_PROMPT`, the `[source: ...]` prefix in
`format_docs`, and the article_id→chunk_id normalization in `answer_question` (the model
sometimes cites the shorter article_id instead of the full chunk_id).

## 8. Refusal examples

All 3 out-of-corpus questions correctly refused, verbatim:

1. **Q:** What's the refund policy if I cancel my subscription in the middle of a billing cycle?
   **A:** I don't know — the help center articles I have don't cover that.
2. **Q:** Can I still recover a file after its trash retention period has ended?
   **A:** I don't know — the help center articles I have don't cover that.
3. **Q:** Is there a native desktop app for Linux?
   **A:** I don't know — the help center articles I have don't cover that.

The system prompt forces this exact sentence rather than suggesting the model "use its best
judgement" on thin context. That keeps out-of-corpus questions from being answered with guesses
from nearby but insufficient context.

## 9. Generic/ambiguous question

**Q:** "How do I stop getting notifications?"
**Retrieved article IDs (top-5, section_aware, unfiltered):** `kb-notify-005, kb-notify-005,
kb-notify-005, kb-notify-005, kb-notify-005`

The question is genuinely ambiguous because notification behavior exists in both the notifications
and mobile contexts. In the current unfiltered retrieval, however, all five retrieved chunks come
from kb-notify-005. The metadata filtering experiment demonstrates that applying
product_area=mobile changes the Top-1 result to kb-mobile-004.

## 10. Final chunking strategy: keeping section_aware

section_aware ships. All three strategies tie on article-level Hit@3 and Hit@5: each reports
8/8 at both cutoffs. The choice is therefore not based on a higher Hit@5.

section_aware preserves Markdown section structure: each `##` section stays together, and tables
remain with their headers and rows instead of being split into fragments. That improves
chunk-level context for troubleshooting-table questions, where a row without its header can be
harder to interpret or rank correctly. section_aware also produces fewer chunks than
recursive_small, reducing index fragmentation while preserving equivalent measured retrieval
coverage.

Therefore section_aware is selected based on structural coherence and equivalent measured
retrieval coverage, not because it has a higher Hit@5. For a KB with much longer sections, a
hybrid approach would be the next thing to try: section-aware splitting first, then a secondary
size cap only for oversized sections.

## 12. Week 4 — Debugging retrieval: failure labeling and one measured fix

Reproduce with `.venv\Scripts\python -m src.scripts.debug_retrieval` (raw output:
`results/debug_retrieval.json`). Uses the shipped `section_aware` collection, k=3.

### 12.1 Finding failing questions

The 8 known-answer questions from section 2 all hit 8/8 at Top-3 for every chunking strategy —
this KB is too small for hit-rate@3 to break on single-topic questions. Real failures showed up
once the questions became **compound**: a question that genuinely blends two support topics
(e.g. "session/logout" + "upload"), where the weaker topic's article can get crowded out of
retrieval entirely by the stronger one.

6 such questions were built and run through baseline (semantic-only) retrieval:

| # | Question | Expected | Baseline Top-3 | Hit@3 |
|---|---|---|---|---|
| 1 | "I keep getting logged out and my files won't upload, what's going on?" | kb-account-001 | mobile-004, sync-002, mobile-004 | ❌ |
| 2 | "My files keep failing to upload and I had to sign in again, why?" | kb-account-001 | sync-002, sync-002, errors-006 | ❌ |
| 3 | "Every time I try to sync a big file my session ends and I'm logged out" | kb-account-001 | sync-002 ×3 | ❌ |
| 4 | "Nothing uploads and I don't get any alerts about it either" | kb-sync-002 | notify-005, notify-005, mobile-004 | ❌ |
| 5 | "My account keeps disconnecting whenever I try to move a lot of files" | kb-account-001 | sync-002 ×3 | ❌ |
| 6 | "My connection to the workspace drops during big file transfers, why?" | kb-account-001 | sync-002 ×3 | ❌ |

**Baseline hit-rate@3: 0/6.**

### 12.2 Labeling: wrong document fetched, in all 6 cases

For every failure, the expected article was checked against a wider Top-10 pool. In **all 6**,
the expected article is **absent even from Top-10** — not just poorly ranked, genuinely never
retrieved. That makes every one of these a **"wrong document fetched"** failure, not a
generation failure: the LLM never had a chance, because the retrieval step never handed it the
right source. (None of the 6 produced the other failure kind — "right document, wrong answer" —
because none of them got the right document into context in the first place. That category is
implemented and checked in `debug_retrieval.py` whenever `GROQ_API_KEY` is set — running it here
had no key configured, so it's unexercised, not disproven.)

### 12.3 First hypothesis, ruled out: reranking

Reranking is the cheapest lever already in the app, so it was checked first. It **did not fix a
single one** — reranked hit-rate@3 stayed **0/6**. This is expected, not a bug: reranking only
reorders whatever the initial semantic search already retrieved into its candidate pool. If the
correct article was never in that pool (as confirmed in 12.2), there is nothing for reranking to
promote. This mirrors the module's own framing: switching to a better ranker doesn't fix a
retrieval-fetch problem, since the ranker never sees what was never fetched.

### 12.4 The one change measured: hybrid search

Hybrid search (semantic + a keyword-overlap pass, `use_hybrid=True` in `src/rag/chain.py`) was
applied as the single change, because it targets the actual mechanism of these failures: literal
words like "logged out" and "session" are exactly what keyword scoring catches, even when the
embedding model let them get diluted by the sync/upload half of the question.

| # | Question | Hybrid Top-3 | Hit@3 |
|---|---|---|---|
| 1 | logged out + upload | mobile-004, sync-002, sync-002 | ❌ |
| 2 | upload + sign in again | sync-002, sync-002, sync-002 | ❌ |
| 3 | sync + session ends + logged out | sync-002, **account-001**, sync-002 | ✅ |
| 4 | uploads + alerts | notify-005, notify-005, notify-005 | ❌ |
| 5 | account disconnecting + move files | sync-002, errors-006, sync-002 | ❌ |
| 6 | connection drops + file transfers | sync-002, errors-006, sync-002 | ❌ |

**Hybrid hit-rate@3: 1/6 — up from 0/6 baseline (and 0/6 reranked).**

A real, if modest, win: one genuine fetch failure recovered, from a change that touches nothing
about generation or ranking — only which documents make it into the candidate pool at all.

### 12.5 What the fix did not fix

5 of 6 stayed misses even with hybrid search on. Question 3, the one that got fixed, uses the
literal words "session" and "logged out" — exactly what keyword scoring catches. The other five
either don't contain enough of `kb-account-001`'s literal vocabulary for keyword overlap to catch
(questions 1, 2, 5, 6 — phrased around "won't upload", "sign in again", "disconnecting",
"connection drops" rather than "session"/"logged out") or keyword-match toward the wrong article
entirely (question 4, "uploads" + "alerts" pulls toward `kb-notify-005`, not the expected
`kb-sync-002`). Naive keyword overlap only helps when the query happens to reuse the source
article's own words — it doesn't help when the user's phrasing and the article's phrasing just
don't share vocabulary. Fixing the remainder would need query decomposition/rewriting (splitting
a compound question into its two intents before retrieving) rather than another retrieval-side
tweak — deferred, not attempted, to keep this to one change.

### 12.6 Not part of the measured change

`src/rag/chain.py` also exposes `use_rerank` (real cross-encoder, checked above, ruled out for
this failure set — not disabled, still useful for other cases) and a hybrid toggle in the
Streamlit UI. Only hybrid search is what's reported as "the fix" above; reranking stayed in the
app because it's a real, working feature, just not the one that moved this number.

### 12.7 A note on how this was run

This ran through the actual shipped app end-to-end (`.venv\Scripts\python -m
src.scripts.debug_retrieval`) — not a simulation. The vector backend is FAISS
(`VECTOR_BACKEND=faiss`, the default in `src/rag/config.py`), not Qdrant: the dev machine used for
this write-up has a Windows Application Control Policy that blocks `qdrant-client`'s (and, it
turns out, `chromadb`'s) grpc native extension outright. FAISS has no grpc dependency at all.
`src/rag/vectorstore.py` keeps the Qdrant code path fully intact behind that one env var —
`VECTOR_BACKEND=qdrant` switches back with no code changes, for a machine without that
restriction.

## 13. Scope note

This is a fresh 6-article mock KB built for this practical, not a re-index of a larger historical
corpus — ingestion (`src/scripts/ingest.py`) only ever touches `data/kb/`.

## Appendix A — Per-question search-only retrieval dump

Search-only retrieval evidence from `results/chunking_strategy_comparison.json`. Top-3 lists ranks 1-3; Top-5 lists only the additional ranks 4-5.

### Q1 — How long does a password reset link stay valid before it expires?

Expected article:
`kb-account-001`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-account-001` — `kb-account-001::recursive_small::38` — score `0.5728`
  2. `kb-account-001` — `kb-account-001::recursive_small::31` — score `0.5448`
  3. `kb-errors-006` — `kb-errors-006::recursive_small::12` — score `0.5126`
- Top-5:
  4. `kb-account-001` — `kb-account-001::recursive_small::11` — score `0.4573`
  5. `kb-share-003` — `kb-share-003::recursive_small::20` — score `0.4515`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-account-001` — `kb-account-001::recursive_large::12` — score `0.4906`
  2. `kb-account-001` — `kb-account-001::recursive_large::18` — score `0.4293`
  3. `kb-account-001` — `kb-account-001::recursive_large::10` — score `0.4177`
- Top-5:
  4. `kb-account-001` — `kb-account-001::recursive_large::13` — score `0.4096`
  5. `kb-errors-006` — `kb-errors-006::recursive_large::4` — score `0.3843`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-account-001` — `kb-account-001::section_aware::6` — score `0.4696`
  2. `kb-account-001` — `kb-account-001::section_aware::10` — score `0.4293`
  3. `kb-account-001` — `kb-account-001::section_aware::5` — score `0.4123`
- Top-5:
  4. `kb-account-001` — `kb-account-001::section_aware::1` — score `0.3414`
  5. `kb-account-001` — `kb-account-001::section_aware::8` — score `0.3352`

### Q2 — When two devices edit the same file before syncing, what happens to the older version?

Expected article:
`kb-sync-002`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_small::8` — score `0.6567`
  2. `kb-sync-002` — `kb-sync-002::recursive_small::30` — score `0.5257`
  3. `kb-sync-002` — `kb-sync-002::recursive_small::4` — score `0.523`
- Top-5:
  4. `kb-sync-002` — `kb-sync-002::recursive_small::11` — score `0.5199`
  5. `kb-sync-002` — `kb-sync-002::recursive_small::19` — score `0.5079`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-sync-002` — `kb-sync-002::recursive_large::0` — score `0.4875`
  2. `kb-sync-002` — `kb-sync-002::recursive_large::1` — score `0.462`
  3. `kb-sync-002` — `kb-sync-002::recursive_large::2` — score `0.4289`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_large::2` — score `0.4272`
  5. `kb-sync-002` — `kb-sync-002::recursive_large::6` — score `0.4084`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-sync-002` — `kb-sync-002::section_aware::1` — score `0.551`
  2. `kb-sync-002` — `kb-sync-002::section_aware::2` — score `0.4596`
  3. `kb-errors-006` — `kb-errors-006::section_aware::3` — score `0.448`
- Top-5:
  4. `kb-sync-002` — `kb-sync-002::section_aware::3` — score `0.4216`
  5. `kb-sync-002` — `kb-sync-002::section_aware::0` — score `0.4145`

### Q3 — What is the maximum size allowed for a single file upload?

Expected article:
`kb-sync-002`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_small::10` — score `0.6509`
  2. `kb-sync-002` — `kb-sync-002::recursive_small::20` — score `0.5135`
  3. `kb-sync-002` — `kb-sync-002::recursive_small::7` — score `0.4869`
- Top-5:
  4. `kb-sync-002` — `kb-sync-002::recursive_small::4` — score `0.4348`
  5. `kb-sync-002` — `kb-sync-002::recursive_small::23` — score `0.4291`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_large::2` — score `0.4248`
  2. `kb-sync-002` — `kb-sync-002::recursive_large::5` — score `0.3636`
  3. `kb-sync-002` — `kb-sync-002::recursive_large::1` — score `0.3563`
- Top-5:
  4. `kb-sync-002` — `kb-sync-002::recursive_large::2` — score `0.3502`
  5. `kb-sync-002` — `kb-sync-002::recursive_large::6` — score `0.3099`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::section_aware::3` — score `0.4157`
  2. `kb-sync-002` — `kb-sync-002::section_aware::5` — score `0.3721`
  3. `kb-sync-002` — `kb-sync-002::section_aware::2` — score `0.3511`
- Top-5:
  4. `kb-sync-002` — `kb-sync-002::section_aware::3` — score `0.3402`
  5. `kb-errors-006` — `kb-errors-006::section_aware::5` — score `0.3199`

### Q4 — Can someone with the Commenter role edit the actual content of a document?

Expected article:
`kb-share-003`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-share-003` — `kb-share-003::recursive_small::9` — score `0.3168`
  2. `kb-share-003` — `kb-share-003::recursive_small::24` — score `0.3115`
  3. `kb-errors-006` — `kb-errors-006::recursive_small::17` — score `0.2799`
- Top-5:
  4. `kb-share-003` — `kb-share-003::recursive_small::0` — score `0.2708`
  5. `kb-share-003` — `kb-share-003::recursive_small::23` — score `0.2564`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-share-003` — `kb-share-003::recursive_large::7` — score `0.2525`
  2. `kb-share-003` — `kb-share-003::recursive_large::5` — score `0.2`
  3. `kb-share-003` — `kb-share-003::recursive_large::0` — score `0.1929`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_large::5` — score `0.1633`
  5. `kb-share-003` — `kb-share-003::recursive_large::2` — score `0.1553`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-share-003` — `kb-share-003::section_aware::6` — score `0.2525`
  2. `kb-share-003` — `kb-share-003::section_aware::0` — score `0.2009`
  3. `kb-share-003` — `kb-share-003::section_aware::3` — score `0.1592`
- Top-5:
  4. `kb-share-003` — `kb-share-003::section_aware::8` — score `0.1519`
  5. `kb-notify-005` — `kb-notify-005::section_aware::6` — score `0.1457`

### Q5 — If I turn off email notifications for every individual event, does that also stop the weekly digest email?

Expected article:
`kb-notify-005`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-notify-005` — `kb-notify-005::recursive_small::12` — score `0.5966`
  2. `kb-notify-005` — `kb-notify-005::recursive_small::20` — score `0.5225`
  3. `kb-notify-005` — `kb-notify-005::recursive_small::5` — score `0.5215`
- Top-5:
  4. `kb-notify-005` — `kb-notify-005::recursive_small::22` — score `0.3981`
  5. `kb-notify-005` — `kb-notify-005::recursive_small::9` — score `0.3944`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-notify-005` — `kb-notify-005::recursive_large::3` — score `0.5887`
  2. `kb-notify-005` — `kb-notify-005::recursive_large::5` — score `0.4291`
  3. `kb-notify-005` — `kb-notify-005::recursive_large::0` — score `0.4114`
- Top-5:
  4. `kb-notify-005` — `kb-notify-005::recursive_large::6` — score `0.3925`
  5. `kb-notify-005` — `kb-notify-005::recursive_large::8` — score `0.3674`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-notify-005` — `kb-notify-005::section_aware::1` — score `0.4494`
  2. `kb-notify-005` — `kb-notify-005::section_aware::6` — score `0.4291`
  3. `kb-notify-005` — `kb-notify-005::section_aware::7` — score `0.3948`
- Top-5:
  4. `kb-notify-005` — `kb-notify-005::section_aware::4` — score `0.3904`
  5. `kb-notify-005` — `kb-notify-005::section_aware::2` — score `0.3728`

### Q6 — What does error code NB‑SYNC‑101 mean and how do I fix it?

Expected article:
`kb-errors-006`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-sync-002` — `kb-sync-002::recursive_small::14` — score `0.822`
  2. `kb-errors-006` — `kb-errors-006::recursive_small::30` — score `0.6828`
  3. `kb-errors-006` — `kb-errors-006::recursive_small::4` — score `0.6795`
- Top-5:
  4. `kb-mobile-004` — `kb-mobile-004::recursive_small::15` — score `0.6457`
  5. `kb-errors-006` — `kb-errors-006::recursive_small::21` — score `0.5603`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_large::10` — score `0.7418`
  2. `kb-errors-006` — `kb-errors-006::recursive_large::7` — score `0.6427`
  3. `kb-errors-006` — `kb-errors-006::recursive_large::0` — score `0.6299`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_large::9` — score `0.5635`
  5. `kb-sync-002` — `kb-sync-002::recursive_large::3` — score `0.5587`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::section_aware::8` — score `0.7418`
  2. `kb-errors-006` — `kb-errors-006::section_aware::1` — score `0.6869`
  3. `kb-errors-006` — `kb-errors-006::section_aware::5` — score `0.6332`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::section_aware::7` — score `0.5545`
  5. `kb-sync-002` — `kb-sync-002::section_aware::7` — score `0.5337`

### Q7 — I got NB-AUTH-410 when using my password reset link — what does that mean?

Expected article:
`kb-errors-006`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_small::12` — score `0.6788`
  2. `kb-errors-006` — `kb-errors-006::recursive_small::14` — score `0.5445`
  3. `kb-errors-006` — `kb-errors-006::recursive_small::13` — score `0.5427`
- Top-5:
  4. `kb-account-001` — `kb-account-001::recursive_small::25` — score `0.4717`
  5. `kb-account-001` — `kb-account-001::recursive_small::38` — score `0.4521`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_large::4` — score `0.6099`
  2. `kb-account-001` — `kb-account-001::recursive_large::12` — score `0.5344`
  3. `kb-account-001` — `kb-account-001::recursive_large::8` — score `0.462`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_large::10` — score `0.4378`
  5. `kb-account-001` — `kb-account-001::recursive_large::10` — score `0.4167`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-account-001` — `kb-account-001::section_aware::6` — score `0.5041`
  2. `kb-errors-006` — `kb-errors-006::section_aware::8` — score `0.4378`
  3. `kb-account-001` — `kb-account-001::section_aware::5` — score `0.4294`
- Top-5:
  4. `kb-account-001` — `kb-account-001::section_aware::8` — score `0.4148`
  5. `kb-account-001` — `kb-account-001::section_aware::4` — score `0.3985`

### Q8 — What should I do about error code NB-SHARE-512?

Expected article:
`kb-errors-006`

#### recursive_small

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_small::16` — score `0.6044`
  2. `kb-sync-002` — `kb-sync-002::recursive_small::14` — score `0.59`
  3. `kb-errors-006` — `kb-errors-006::recursive_small::4` — score `0.579`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_small::17` — score `0.5766`
  5. `kb-errors-006` — `kb-errors-006::recursive_small::22` — score `0.5473`

#### recursive_large

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::recursive_large::5` — score `0.6305`
  2. `kb-errors-006` — `kb-errors-006::recursive_large::0` — score `0.6174`
  3. `kb-errors-006` — `kb-errors-006::recursive_large::7` — score `0.5718`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::recursive_large::10` — score `0.525`
  5. `kb-sync-002` — `kb-sync-002::recursive_large::3` — score `0.5233`

#### section_aware

- Hit@3: true
- Hit@5: true
- Top-3:
  1. `kb-errors-006` — `kb-errors-006::section_aware::1` — score `0.5777`
  2. `kb-errors-006` — `kb-errors-006::section_aware::5` — score `0.5643`
  3. `kb-errors-006` — `kb-errors-006::section_aware::0` — score `0.5446`
- Top-5:
  4. `kb-errors-006` — `kb-errors-006::section_aware::8` — score `0.525`
  5. `kb-errors-006` — `kb-errors-006::section_aware::7` — score `0.4395`
