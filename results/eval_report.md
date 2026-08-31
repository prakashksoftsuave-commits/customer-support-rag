# Evals — Measuring Whether a Change Actually Helped (Week 6)

One command: `.venv\Scripts\python -m src.scripts.run_evals`. Runs the full suite, validates the
judge first, then reports before/after per problem type. Raw output: `results/eval_report.json`.
Suite definition: `data/eval/eval_suite.json` (22 cases, 8 problem types, built directly from
Week 4's failure labels and Week 5's real-trace findings).

## 1. Free checks first

Every case gets three rule-based checks before any LLM judge call, because they're free and a
rule can answer them outright: did it refuse exactly when it should (and not otherwise)? did the
right article show up in retrieval when one was expected? is a `[source: ...]` citation present
on a non-refusing answer? All three have to pass for `rule_pass` — strict, on purpose, since a
correct-sounding answer that's missing its citation isn't actually the deliverable Week 3 asked
for.

## 2. Judge validation — checked before trusting it

**First attempt failed, and that failure is itself worth recording.** The first version of the
validation subset picked cases the app *wrongly refuses* (from Week 4/5's known failures) and
labeled them "fail" — but the judge only ever scores a real answer; on a refusal it never runs at
all. Comparing "fail" against "never ran" isn't judge disagreement, it's a subset built to test
the wrong thing — refusal-correctness is already the rule-based check's job, not the judge's.
Fixed by restricting the validation subset to cases where the app actually answers, so the
judge's grading can be checked against a real judgment call:

| Case | Human label | Judge pass | Agree? |
|---|---|---|---|
| known_01, known_02, known_03, known_04, known_06 | pass | pass | Yes (5/5) |
| ambiguous_01 | pass | pass | Yes |
| compound_05 | pass | pass | Yes |
| scope_01 | **fail** | pass | **No** |

**Agreement: 7/8 (88%)** — above the bar to trust the judge's scores below.

The one disagreement is explained, not just noted: `scope_01`'s answer tells the user that
Nimbus's "restrict sharing to workspace" setting will keep a folder visible "solely to your
team" — but workspace and team aren't the same scope, and the KB never equates them. Every
individual sentence in that answer IS grounded in a real chunk (which is exactly what the judge's
faithfulness rubric checks, sentence by sentence), so the judge correctly finds no single
unsupported claim — it just can't see that *combining* two true chunks produced a misleading
implication no single chunk stated. That's a real limitation of a per-claim faithfulness judge,
not a broken judge: it catches hallucination, not synthesis-level overclaims across chunks.

## 3. The one change: query decomposition

Implementing Week 5's prediction — `decompose_query()` in `src/rag/chain.py` splits a question
into up to 2 single-topic sub-questions (one small LLM call) before retrieving; `k` docs are
pulled per sub-question and interleaved, capped at `k` total so it stays directly comparable to
plain retrieval at the same `k`. Toggled by `use_decompose=True` in `answer_question()` — hybrid
and rerank stay off for this comparison, so only one variable moves.

## 4. Before → after, per problem type

| Problem type | Baseline rule_pass | After rule_pass | Moved? |
|---|---|---|---|
| **compound_retrieval** | 0.00 (0/5) | **0.40 (2/5)** | Yes — the target |
| exact_code_lookup | 0.00 (0/2) | 0.00 (0/2) | No — correctly untouched |
| known_answer | 1.00 (6/6) | 1.00 (6/6) | No regression |
| out_of_corpus | 1.00 (3/3) | 1.00 (3/3) | No regression |
| scope_conflation | 1.00 (1/1) | 1.00 (1/1) | No regression |
| ambiguous | 1.00 (1/1) | 1.00 (1/1) | No regression |
| meta_question | 0.00 (0/1) | 1.00 (1/1) | See caveat below |
| vague_input | n/a | n/a | Not asserted yet (see §5) |

**compound_retrieval moved from 0/5 to 2/5** (`compound_01` and `compound_02` both flipped from a
wrong refusal to a correct, cited answer retrieving `kb-account-001`) — a real, reproducible
result: this exact 2/5 split showed up identically in two separate full runs of the suite.
Widening the lens beyond the strict rule: baseline only *attempted* a real answer on 1 of 5
compound questions; after decomposition, 3 of 5 attempted one, and every attempt that did
happen — before and after — passed the judge on faithfulness and relevancy. So decomposition's
actual effect is "answers instead of refusing" more often; the remaining 2/5 gap
(`compound_03`, `compound_04`) is still a pure retrieval-coverage problem, not a generation one —
those two never surfaced `kb-account-001` even from the decomposed sub-questions. `src/scripts/run_evals.py`
doesn't currently log what the decomposer actually split those into, which is the natural next
debugging step and a real gap in this week's tooling, not something fixed here.

**exact_code_lookup correctly stayed at 0/2** — exactly what Week 5's diagnosis predicted:
decomposition only helps a question that's blending two topics; `NB-AUTH-410` and `NB-SHARE-512`
are single-topic exact-code lookups with nothing to split, so the fix correctly did nothing to a
failure mode it wasn't built for. That's this week's evidence that the earlier diagnosis (fetch
failure vs. table-row-chunk failure are different mechanisms) was right, and it points at what
Week 5's other ranked problem — the missed table-row chunk — will actually need: something at the
chunking or retrieval-ranking level, not query decomposition.

**Caveat on `meta_question`:** it flipped from refusing to answering — but re-running the exact
same question, same config, twice already produced three different behaviors across this week
(a full answer in Week 5's trace, a refusal in this week's first baseline run, an answer again in
the "after" run). Groq's serving stack isn't perfectly deterministic even at `temperature=0`, so
this one flip is not attributed to query decomposition — there's no plausible mechanism by which
splitting an already-single-topic meta-question into sub-questions would fix it, and the more
likely explanation is sampling noise. Flagged rather than counted as a win. A more rigorous setup
would run each case multiple times and report a rate, not a single before/after snapshot — that's
a real limitation of this week's suite, not swept under the rug.

**Prediction check against Week 5:** Week 5 predicted compound-question hit-rate would reach
roughly 4-5/6 after decomposition. The actual result — 2/5 — is a real, positive, reproducible
improvement, but well short of that prediction. The predicted mechanism (single-topic sub-queries
retrieve fine, per Week 3's 8/8) was directionally right; it undersold how often the decomposer
itself would fail to produce sub-questions that actually retrieve the weaker topic. Worth
recording as a miss on the prediction's *magnitude*, not its direction.

## 5. What's not covered yet

`vague_input` (the "help" case) has no rule defined — Week 5 flagged it as a UX gap, not a
correctness bug, and there's no clean assertion for "did the app respond helpfully to a greeting"
yet. It's in the suite and gets run every time, but it contributes no pass/fail signal until
that's designed. Listed here instead of silently dropped.
