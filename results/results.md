# Results — Nimbus Help Center RAG

A "ask my documents" app over a 6-article mock help-center KB for Nimbus, a fictional cloud
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
against its resolved chunk:

1. **Q:** How long does a password reset link stay valid before it expires?
   **A:** A password reset link is valid for 30 minutes for security reasons [source: kb-account-001::section_aware::6].
   *Verified citation chunk: `kb-account-001::section_aware::6`.*

2. **Q:** Can someone with the Commenter role edit the actual content of a document?
   **A:** No, a Commenter can only add comments without editing the content [source: kb-share-003::section_aware::6].
   *Verified citation chunk: `kb-share-003::section_aware::6`.*

3. **Q (table-based):** What does error code NB-SYNC-101 mean and how do I fix it?
   **A:** The error code `NB‑SYNC‑101` may appear briefly during rapid file edits but resolves automatically [source: kb-errors-006::section_aware::8].
   *Verified citation chunk: `kb-errors-006::section_aware::8`.*

## 8. Refusal examples

All 3 out-of-corpus questions correctly refused, verbatim:

1. **Q:** What's the refund policy if I cancel my subscription in the middle of a billing cycle?
   **A:** I don't know — the help center articles I have don't cover that.
2. **Q:** Can I still recover a file after its trash retention period has ended?
   **A:** I don't know — the help center articles I have don't cover that.
3. **Q:** Is there a native Nimbus desktop app for Linux?
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

## 11. Scope note

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
