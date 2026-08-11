"""Compare retrieval across chunking strategies (and chunk-size/overlap within one strategy),
at both Top-3 and Top-5, on the same 8 known-answer questions."""

import json

from src.rag.config import CHUNK_PROFILES, ROOT_DIR
from src.rag.vectorstore import get_vectorstore

TOP_KS = [3, 5]
QUESTIONS_PATH = ROOT_DIR / "data" / "eval" / "questions.json"
OUT_PATH = ROOT_DIR / "results" / "chunking_strategy_comparison.json"


def hit_rate(vectorstore, questions, k):
    hits = 0
    per_question = []
    for q in questions:
        results = vectorstore.similarity_search_with_score(q["question"], k=k)
        retrieved_article_ids = [doc.metadata["article_id"] for doc, _ in results]
        hit = q["expected_article_id"] in retrieved_article_ids
        hits += hit
        per_question.append({
            "question": q["question"],
            "table_based": q["table_based"],
            "expected_article_id": q["expected_article_id"],
            "retrieved": [
                {
                    "article_id": doc.metadata["article_id"],
                    "chunk_id": doc.metadata["chunk_id"],
                    "score": round(score, 4),
                }
                for doc, score in results
            ],
            "hit": hit,
        })
    return hits, per_question


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text())["known_answer_questions"]

    report = {"profiles": {}}
    for profile in CHUNK_PROFILES:
        vectorstore = get_vectorstore(profile.collection)
        profile_report = {
            "strategy": profile.strategy,
            "chunk_size": profile.chunk_size,
            "chunk_overlap": profile.chunk_overlap,
        }
        for k in TOP_KS:
            hits, per_question = hit_rate(vectorstore, questions, k)
            profile_report[f"hit_in_top_{k}"] = f"{hits}/{len(questions)}"
            profile_report[f"per_question_top_{k}"] = per_question
            print(f"[{profile.name}] hit-in-top-{k}: {hits}/{len(questions)}")
        report["profiles"][profile.name] = profile_report

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
