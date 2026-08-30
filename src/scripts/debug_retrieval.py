"""Week 4: take failing questions, label each as 'wrong document fetched' vs 'right document,
wrong answer', then measure hit-rate@3 before/after exactly one change.

Reranking is checked first since it's the cheapest lever already in the app, but it only
reorders whatever the initial semantic search already retrieved — it cannot fix a question
whose correct article never made that candidate pool. Hybrid (semantic + keyword) search is
the one change actually measured, because these failures are all "wrong document fetched":
literal words the embedding underweights (e.g. "logged out", "session") are exactly what
keyword scoring picks up.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json

from src.rag.chain import PROMPT, REFUSAL_TEXT, format_docs, get_llm, get_reranker, rerank_docs, retrieve
from src.rag.config import ROOT_DIR, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore

K = 3
WIDE_POOL = 10  # how far to look when a question misses top-K, to see if the doc exists at all
QUESTIONS_PATH = ROOT_DIR / "data" / "eval" / "failing_questions.json"
OUT_PATH = ROOT_DIR / "results" / "debug_retrieval.json"


def hit(article_ids: list[str], expected: str) -> bool:
    return expected in article_ids[:K]


def label_failure(vectorstore, llm, q: dict, baseline_ids: list[str], baseline_hit: bool) -> dict:
    if baseline_hit:
        if llm is None:
            return {"kind": "not_checked", "evidence": "hit at baseline; generation not checked (no GROQ_API_KEY)"}
        docs = vectorstore.similarity_search(q["question"], k=K)
        chain = PROMPT | llm
        answer = chain.invoke({"context": format_docs(docs), "question": q["question"]}).content
        correct = answer.strip() != REFUSAL_TEXT
        return {
            "kind": "right_document_correct_answer" if correct else "right_document_wrong_answer",
            "evidence": f"generated answer: {answer!r}",
        }
    wide_ids = [d.metadata["article_id"] for d in vectorstore.similarity_search(q["question"], k=WIDE_POOL)]
    rank = wide_ids.index(q["expected_article_id"]) + 1 if q["expected_article_id"] in wide_ids else None
    return {
        "kind": "wrong_document_fetched",
        "evidence": (f"expected {q['expected_article_id']} exists at rank {rank} in top-{WIDE_POOL}" if rank
                     else f"expected {q['expected_article_id']} absent even from top-{WIDE_POOL}"),
    }


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["failing_questions"]
    vectorstore = get_vectorstore(SECTION_AWARE.collection)
    reranker = get_reranker()
    llm = get_llm() if os.getenv("GROQ_API_KEY") else None

    baseline_hits = reranked_hits = hybrid_hits = 0
    per_question = []
    for q in questions:
        baseline_docs = vectorstore.similarity_search(q["question"], k=K)
        baseline_ids = [d.metadata["article_id"] for d in baseline_docs]
        baseline_hit = hit(baseline_ids, q["expected_article_id"])

        wide_docs = vectorstore.similarity_search(q["question"], k=WIDE_POOL)
        reranked_ids = [d.metadata["article_id"] for d in rerank_docs(wide_docs, q["question"], reranker)[:K]]
        reranked_hit = hit(reranked_ids, q["expected_article_id"])

        hybrid_ids = [d.metadata["article_id"] for d in retrieve(vectorstore, q["question"], k=K, use_hybrid=True)]
        hybrid_hit = hit(hybrid_ids, q["expected_article_id"])

        baseline_hits += baseline_hit
        reranked_hits += reranked_hit
        hybrid_hits += hybrid_hit

        failure = label_failure(vectorstore, llm, q, baseline_ids, baseline_hit)
        per_question.append({
            "question": q["question"],
            "expected_article_id": q["expected_article_id"],
            "note": q["note"],
            "baseline_top3": baseline_ids,
            "baseline_hit": baseline_hit,
            "reranked_top3": reranked_ids,
            "reranked_hit": reranked_hit,
            "hybrid_top3": hybrid_ids,
            "hybrid_hit": hybrid_hit,
            "fixed_by_hybrid": (not baseline_hit) and hybrid_hit,
            "failure_label": failure["kind"],
            "failure_evidence": failure["evidence"],
        })
        print(f"[baseline {'HIT ' if baseline_hit else 'MISS'} | rerank {'HIT ' if reranked_hit else 'MISS'} "
              f"| hybrid {'HIT' if hybrid_hit else 'MISS'}] {q['question']}  ({failure['kind']})")

    n = len(questions)
    report = {
        "k": K,
        "baseline_hit_rate_at_3": f"{baseline_hits}/{n}",
        "reranked_hit_rate_at_3": f"{reranked_hits}/{n}",
        "hybrid_hit_rate_at_3": f"{hybrid_hits}/{n}",
        "one_change_measured": "hybrid search (semantic + keyword)",
        "per_question": per_question,
    }
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nBaseline hit-rate@3:  {baseline_hits}/{n}")
    print(f"Reranked hit-rate@3:  {reranked_hits}/{n}  (checked, not the change we're shipping)")
    print(f"Hybrid hit-rate@3:    {hybrid_hits}/{n}  (the one change)")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
