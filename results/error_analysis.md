# Error Analysis — Reading Traces Like a Professional (Week 5)

20 real traces, collected live against the deployed app config (`section_aware`, k=4, no hybrid,
no rerank — what a real user actually hits), read one by one, before any category names were
decided. Raw traces: `data/traces/week5_batch.jsonl`. Reproduce with
`.venv\Scripts\python -m src.scripts.collect_traces`.

## 1. Sampling — not cherry-picked

Pool of 33 candidate questions, sampled down to 20 with a fixed seed (`random.Random(42)`, in
`src/scripts/collect_traces.py`) so the sample is reproducible and auditable, not hand-picked:

- 8 known-answer questions (Week 3)
- 1 ambiguous question, 3 out-of-corpus questions (Week 3)
- 6 compound questions already known to fail retrieval (Week 4)
- 15 new questions written for this week specifically to avoid a pool of only "nice examples" —
  typos, one-word input, gibberish, a meta question about the assistant itself, multi-part
  questions, and questions requiring the model to synthesize across two facts rather than quote
  one chunk.

20 of the 33 were drawn; 13 didn't make the sample (sampling, not selection, decided that).

## 2. Reading each trace — honest notes, failures only

15 of 20 were correct, well-cited, or correctly refused (t02, t04, t06, t07, t08, t09, t10, t12,
t13, t15, t16, t17, t19 — plus t11 and t20, addressed separately below). The failures:

- **t01** — *"What should I do about error code NB-SHARE-512?"* Retrieved only generic
  error-reference chunks (overview, an unrelated FAQ, internal notes); the actual "Sharing
  Errors" table row containing NB-SHARE-512 was never in the top-4, so the app said it didn't
  know despite the KB directly covering this code.

- **t03** — *"What can you help me with?"* Answered a vague meta-question using whatever four
  unrelated chunks retrieval happened to return (notifications, error-doc-usage, two account
  FAQs), and presented that arbitrary slice as if it were the complete list of what the app can
  help with — sync, sharing, and mobile don't appear at all.

- **t05** — *"help"* Got the same flat "I don't know — the help center articles I have don't
  cover that" used for genuinely out-of-corpus questions. Technically not wrong, but reads as
  broken rather than helpful for a one-word greeting-style input.

- **t14** — *"My files keep failing to upload and I had to sign in again, why?"* Never retrieved
  any account/session content at all, so the app refused a question that's partially answerable
  from the KB. This is the same failure Week 4 already found and only partly fixed (hybrid search
  recovered 1 of 6 questions like this) — this trace is a fresh instance of the same problem, not
  a new one.

- **t18** — *"I got NB-AUTH-410 when using my password reset link — what does that mean?"* Same
  pattern as t01: the source article (`kb-errors-006`) is in the corpus and was even
  partially retrieved, but the specific "Account and Sign-In Errors" table row for NB-AUTH-410
  never made the top-4, so a directly-answerable code lookup was wrongly refused.

- **t20** — *"I want to make sure only my team can see a folder, not the whole company — how?"*
  The answer told the user that the KB's "restrict sharing to workspace" setting keeps a folder
  visible only to their team. Workspace and team aren't necessarily the same scope — if the whole
  company is one workspace, this advice wouldn't actually do what the user asked. Retrieval and
  citation were both correct; the model's synthesis overclaimed equivalence the KB doesn't state.

**One note that isn't a failure of the app**: t11 ("My connection to the workspace drops during
big file transfers, why?") was carried over from Week 4's failing-questions set, labeled there as
expecting `kb-account-001`. Reading the actual answer here, the app gave a thorough, correctly
grounded response entirely from `kb-sync-002` (network instability, blocked ports, the 2GB
limit) — a legitimate answer to a legitimately sync-shaped question. My Week 4 ground-truth label
for this question was arguably wrong, not the app's retrieval. Worth remembering: a "failure"
metric is only as good as the ground truth behind it, and this one didn't hold up under an actual
read.

## 3. Named problem groups

Grouping the honest notes above (not before writing them):

| Problem | Traces | What it actually is |
|---|---|---|
| **Missed table-row chunk on exact-code lookups** | t01, t18 | The specific error-code table row a question needs isn't retrieved, even when other chunks from the *same article* are — the generic "how to use this doc" / FAQ chunks outrank the compact, symbol-dense table row for a query that's just an error code. |
| **Compound questions don't retrieve their weaker topic** | t14 (+ 5/6 in Week 4's dedicated set) | Already characterized in Week 4. This trace confirms it's a real, recurring failure mode in ordinary sampling, not an artifact of how Week 4's question set was built. |
| **False completeness on vague/meta queries** | t03 | Because retrieval always returns k chunks regardless of relevance, a vague question gets answered from whatever those k chunks happen to be, framed as if it were a complete answer. |
| **Answer overclaims equivalence between similar KB terms** | t20 | A generation-side issue, not retrieval: correct chunks, but the model states two different scopes ("workspace" vs. "team") are the same thing when the KB never says that. |
| **No handling for greeting/vague input** | t05 | A UX gap: one-word non-questions get the same refusal template built for out-of-corpus topics. |

## 4. Ranked by frequency × severity

| Rank | Problem | Frequency | Severity | Why this rank |
|---|---|---|---|---|
| 1 | Compound questions don't retrieve their weaker topic | 1/20 here, 5/6 in Week 4's targeted set | High — total wrong refusal on a partially-answerable, realistic support message | Highest combined evidence: two independent samples (this one and Week 4's) both find it, and Week 4 already showed hybrid search only fixes 1 in 6 |
| 2 | Missed table-row chunk on exact-code lookups | 2/20 (10%) | High — direct code lookup is a core function of a support bot; wrongly refusing it fails the app's most basic use case | Same severity class as #1, slightly lower measured frequency in this sample |
| 3 | False completeness on vague/meta queries | 1/20 (5%) | Medium — not incorrect information, but misleading framing of the app's own scope | Lower severity: doesn't misinform about the product, only about the app itself |
| 4 | Answer overclaims equivalence between similar KB terms | 1/20 (5%) | Medium — could lead a user to a real security misconfiguration (folder shared company-wide when they wanted team-only) | Ranked above #5 because the downside if acted on is concrete, not cosmetic |
| 5 | No handling for greeting/vague input | 1/20 (5%) | Low — unhelpful, not wrong | Cosmetic UX gap, no incorrect information involved |

## 5. Target for next fix, and the prediction

**Picking #1 — compound questions not retrieving their weaker topic.** Not #2, even though it's
close, because #1 has stronger cross-sample evidence (confirmed in two independent traces sets)
and because Week 4 already tried the cheap fix (hybrid search) and it only reached 1/6 — there's a
known, well-reasoned next lever that hasn't been tried yet: **query decomposition** — split a
compound question into its separate topic-pure sub-questions before retrieving, retrieve each
sub-question independently, then merge the unique retrieved chunks before generation.

**Prediction:** Week 3 already showed single-topic questions hit at 8/8 on this KB — the
retrieval model handles each topic fine in isolation. The failure is specifically that compound
phrasing dilutes the embedding across two topics at once, not that either topic alone is hard to
retrieve. If that diagnosis is right, decomposing a compound question back into its two
single-topic halves before retrieving should recover most of the failures hybrid search couldn't
reach — expect compound-question hit-rate@3 to rise from today's 0/6 baseline (1/6 with hybrid)
to somewhere around 4-5/6 once each half is retrieved on its own. This is a prediction to test
next, not something implemented in this pass — Week 5's task is picking the target and writing
down what's expected, not building the fix yet.
