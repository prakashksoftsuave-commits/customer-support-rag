"""Week 5: collect a fair random sample of real traces (question, retrieved chunks, answer) for
manual error analysis — not a curated set of nice examples. Uses the app's default settings
(section_aware, k=4, no hybrid, no rerank) since that's what a real user actually hits.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.stdout.reconfigure(encoding="utf-8")

import json
import random
from datetime import datetime, timezone

from src.rag.chain import answer_question, get_llm
from src.rag.config import ROOT_DIR, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore

SEED = 42
SAMPLE_SIZE = 20
QUESTIONS_PATH = ROOT_DIR / "data" / "eval" / "questions.json"
FAILING_PATH = ROOT_DIR / "data" / "eval" / "failing_questions.json"
NEW_QUESTIONS_PATH = ROOT_DIR / "data" / "eval" / "new_questions.json"
OUT_PATH = ROOT_DIR / "data" / "traces" / "week5_batch.jsonl"


def load_candidate_pool() -> list[str]:
    known = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    failing = json.loads(FAILING_PATH.read_text(encoding="utf-8"))["failing_questions"]
    new = json.loads(NEW_QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]

    pool = []
    pool += [q["question"] for q in known["known_answer_questions"]]
    pool += [q["question"] for q in known["ambiguous_questions"]]
    pool += known["out_of_corpus_questions"]
    pool += [q["question"] for q in failing]
    pool += new
    return pool


def main() -> None:
    pool = load_candidate_pool()
    sample = random.Random(SEED).sample(pool, min(SAMPLE_SIZE, len(pool)))

    vectorstore = get_vectorstore(SECTION_AWARE.collection)
    llm = get_llm()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for i, question in enumerate(sample, 1):
            trace_id = f"t{i:02d}"
            run_config = {
                "tags": ["week5-trace"],
                "metadata": {"trace_id": trace_id},
                "run_name": f"week5-{trace_id}",
            }
            answer, docs = answer_question(vectorstore, question, llm=llm, k=4, run_config=run_config)
            trace = {
                "trace_id": trace_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "config": {"chunk_profile": SECTION_AWARE.name, "k": 4, "hybrid": False, "rerank": False},
                "retrieved": [
                    {
                        "chunk_id": d.metadata["chunk_id"],
                        "article_id": d.metadata["article_id"],
                        "excerpt": d.page_content[:200].replace("\n", " "),
                    }
                    for d in docs
                ],
                "answer": answer,
            }
            f.write(json.dumps(trace) + "\n")
            print(f"[{trace['trace_id']}] {question}")
            print(f"    -> {answer[:150]}")

    print(f"\nWrote {len(sample)} traces to {OUT_PATH}")


if __name__ == "__main__":
    main()
