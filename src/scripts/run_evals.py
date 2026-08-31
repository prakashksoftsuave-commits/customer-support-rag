"""Week 6: one-command eval suite. Validates the LLM judge against human labels FIRST, then runs
the full suite under baseline vs. query-decomposition, scoring each with free rule-based checks
plus the (now-validated) judge, and reports before/after per problem type.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.stdout.reconfigure(encoding="utf-8")

import json
from collections import defaultdict

from src.rag.chain import REFUSAL_TEXT, answer_question, format_docs, get_llm, judge_answer
from src.rag.config import ROOT_DIR, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore

SUITE_PATH = ROOT_DIR / "data" / "eval" / "eval_suite.json"
OUT_PATH = ROOT_DIR / "results" / "eval_report.json"
JUDGE_PASS_THRESHOLD = 4  # faithfulness AND relevancy must both be >= this to count as a judge pass
AGREEMENT_WARN_BELOW = 0.7


def judge_pass(scores: dict) -> bool | None:
    if scores["faithfulness"] is None or scores["relevancy"] is None:
        return None
    return scores["faithfulness"] >= JUDGE_PASS_THRESHOLD and scores["relevancy"] >= JUDGE_PASS_THRESHOLD


def run_case(vectorstore, llm, case: dict, use_decompose: bool) -> dict:
    answer, docs = answer_question(vectorstore, case["question"], llm=llm, k=4, use_decompose=use_decompose)
    retrieved_ids = [d.metadata["article_id"] for d in docs]
    refused = REFUSAL_TEXT in answer

    expects = case["expects"]
    refusal_correct = None if expects["should_refuse"] is None else (refused == expects["should_refuse"])
    retrieval_hit = None if not expects["expected_article_id"] else (expects["expected_article_id"] in retrieved_ids)
    citation_present = None if refused else ("source:" in answer.lower())
    checks = [c for c in (refusal_correct, retrieval_hit, citation_present) if c is not None]
    rule_pass = all(checks) if checks else None

    scores = {"faithfulness": None, "relevancy": None}
    if not refused:
        scores = judge_answer(llm, case["question"], format_docs(docs), answer)

    return {
        "id": case["id"],
        "problem_type": case["problem_type"],
        "question": case["question"],
        "answer": answer,
        "retrieved_article_ids": retrieved_ids,
        "refused": refused,
        "refusal_correct": refusal_correct,
        "retrieval_hit": retrieval_hit,
        "citation_present": citation_present,
        "rule_pass": rule_pass,
        "judge_faithfulness": scores["faithfulness"],
        "judge_relevancy": scores["relevancy"],
        "judge_pass": judge_pass(scores),
    }


def validate_judge(results_by_id: dict, labels: dict) -> tuple[float, list[dict]]:
    rows = []
    agree = 0
    for case_id, human_label in labels.items():
        r = results_by_id[case_id]
        human_pass = human_label == "pass"
        judge_p = r["judge_pass"]
        matched = judge_p is not None and judge_p == human_pass
        agree += matched
        rows.append({"id": case_id, "human_label": human_label, "judge_pass": judge_p, "agree": matched})
    rate = agree / len(labels)
    return rate, rows


def aggregate(results: list[dict]) -> dict:
    by_type = defaultdict(list)
    for r in results:
        by_type[r["problem_type"]].append(r)
    report = {}
    for ptype, rows in by_type.items():
        rule_rows = [r["rule_pass"] for r in rows if r["rule_pass"] is not None]
        judge_rows = [r["judge_pass"] for r in rows if r["judge_pass"] is not None]
        report[ptype] = {
            "n": len(rows),
            "rule_pass_rate": round(sum(rule_rows) / len(rule_rows), 2) if rule_rows else None,
            "rule_pass_n": len(rule_rows),
            "judge_pass_rate": round(sum(judge_rows) / len(judge_rows), 2) if judge_rows else None,
            "judge_pass_n": len(judge_rows),
        }
    return report


def print_report(title: str, report: dict) -> None:
    print(f"\n--- {title} ---")
    for ptype, stats in sorted(report.items()):
        rule = f"{stats['rule_pass_rate']:.2f} (n={stats['rule_pass_n']})" if stats["rule_pass_rate"] is not None else "n/a"
        judge = f"{stats['judge_pass_rate']:.2f} (n={stats['judge_pass_n']})" if stats["judge_pass_rate"] is not None else "n/a"
        print(f"  {ptype:22s} total={stats['n']}  rule_pass={rule}  judge_pass={judge}")


def main() -> None:
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    cases = suite["cases"]
    vectorstore = get_vectorstore(SECTION_AWARE.collection)
    llm = get_llm()

    print("Running baseline (use_decompose=False)...")
    baseline_results = [run_case(vectorstore, llm, c, use_decompose=False) for c in cases]
    baseline_by_id = {r["id"]: r for r in baseline_results}

    agreement_rate, agreement_rows = validate_judge(baseline_by_id, suite["judge_validation_subset"]["labels"])
    print(f"\n--- Judge validation (against human labels, baseline config) ---")
    for row in agreement_rows:
        mark = "OK" if row["agree"] else "MISMATCH"
        print(f"  [{mark}] {row['id']}: human={row['human_label']}  judge_pass={row['judge_pass']}")
    print(f"Agreement: {agreement_rate:.0%} ({sum(r['agree'] for r in agreement_rows)}/{len(agreement_rows)})")
    if agreement_rate < AGREEMENT_WARN_BELOW:
        print(f"WARNING: agreement below {AGREEMENT_WARN_BELOW:.0%} — judge scores below are not fully trusted.")

    baseline_report = aggregate(baseline_results)
    print_report("Baseline (decompose off)", baseline_report)

    print("\nRunning after (use_decompose=True)...")
    after_results = [run_case(vectorstore, llm, c, use_decompose=True) for c in cases]
    after_report = aggregate(after_results)
    print_report("After (decompose on)", after_report)

    print("\n--- Before -> After, per problem type ---")
    for ptype in sorted(set(baseline_report) | set(after_report)):
        b = baseline_report.get(ptype, {}).get("rule_pass_rate")
        a = after_report.get(ptype, {}).get("rule_pass_rate")
        b_s = f"{b:.2f}" if b is not None else "n/a"
        a_s = f"{a:.2f}" if a is not None else "n/a"
        print(f"  {ptype:22s} rule_pass  {b_s} -> {a_s}")

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "judge_validation": {"agreement_rate": agreement_rate, "rows": agreement_rows},
                "baseline": {"report": baseline_report, "cases": baseline_results},
                "after_decompose": {"report": after_report, "cases": after_results},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
