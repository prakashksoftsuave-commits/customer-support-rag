"""Run cited answers (mixing prose and table-based questions), confirm refusal on
out-of-corpus questions, and show how an ambiguous question spreads across articles."""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.stdout.reconfigure(encoding="utf-8")  # LLM output can contain characters Windows' default console codepage can't print

import json

from src.rag.chain import REFUSAL_TEXT, answer_question, get_llm
from src.rag.config import ROOT_DIR, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore

QUESTIONS_PATH = ROOT_DIR / "data" / "eval" / "questions.json"
OUT_PATH = ROOT_DIR / "results" / "generation_eval.json"
# Two prose-based + one table-based, so citation correctness is checked against both content types.
CITED_INDICES = [0, 3, 5]


def main() -> None:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    vectorstore = get_vectorstore(SECTION_AWARE.collection)
    llm = get_llm()

    known = data["known_answer_questions"]
    cited = []
    for i in CITED_INDICES:
        q = known[i]
        answer, docs = answer_question(vectorstore, q["question"], llm=llm)
        cited.append({
            "question": q["question"],
            "table_based": q["table_based"],
            "answer": answer,
            "source_chunk_ids": [d.metadata["chunk_id"] for d in docs],
        })

    refusals = []
    for question in data["out_of_corpus_questions"]:
        answer, docs = answer_question(vectorstore, question, llm=llm)
        refusals.append({
            "question": question,
            "answer": answer,
            "correctly_refused": REFUSAL_TEXT in answer,
        })

    ambiguous = []
    for q in data["ambiguous_questions"]:
        docs = vectorstore.similarity_search(q["question"], k=5)
        article_ids = [d.metadata["article_id"] for d in docs]
        ambiguous.append({
            "question": q["question"],
            "note": q["note"],
            "retrieved_article_ids": article_ids,
            "spans_multiple_articles": len(set(article_ids)) > 1,
        })

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"cited": cited, "refusals": refusals, "ambiguous": ambiguous}, indent=2), encoding="utf-8"
    )

    print("--- Cited answers ---")
    for c in cited:
        tag = "[table]" if c["table_based"] else "[prose]"
        print(f"{tag} Q: {c['question']}\nA: {c['answer']}\n")
    print("--- Refusals ---")
    for r in refusals:
        status = "OK" if r["correctly_refused"] else "DID NOT REFUSE"
        print(f"[{status}] Q: {r['question']}\nA: {r['answer']}\n")
    print("--- Ambiguous question ---")
    for a in ambiguous:
        print(f"Q: {a['question']}\nRetrieved article_ids: {a['retrieved_article_ids']}\n")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
