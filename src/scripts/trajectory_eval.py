"""Week 8, task 1: find the outcome-vs-trajectory gap — a case where the final answer looks right
even though the agent took a wrong (or no) path to get there.

A single run of this agent isn't credible evidence either way: Week 6 already documented that this
model isn't fully deterministic even at temperature=0. So this runs every ticket N times and reports
the real spread, not one lucky or unlucky sample.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.stdout.reconfigure(encoding="utf-8")

import json
from collections import defaultdict

from src.rag.agent import SupportReActAgent
from src.rag.config import ROOT_DIR
from src.scripts.race_agent_vs_workflow import (
    TEST_TICKETS,
    classify_outcome_vs_trajectory,
    outcome_correct,
    retry_count,
    tool_choice_recall,
    tool_sequence,
)

N_TRIALS = 5
OUT_JSON = ROOT_DIR / "results" / "trajectory_eval.json"
OUT_MD = ROOT_DIR / "results" / "trajectory_eval.md"


def run_trials() -> list[dict]:
    agent = SupportReActAgent(max_steps=5, timeout_sec=40.0)
    trials = []
    for case in TEST_TICKETS:
        print(f"\n[{case['id']}] running {N_TRIALS} trials...")
        for trial_num in range(1, N_TRIALS + 1):
            res = agent.solve(case["ticket"])
            tools_called = tool_sequence(res)
            recall = tool_choice_recall(tools_called, case["expected_tools"])
            ok = outcome_correct(res.final_answer, case["expected_answer_keywords"])
            gap = classify_outcome_vs_trajectory(ok, recall == 1.0)
            print(f"  trial {trial_num}: tools={tools_called} recall={recall} outcome_ok={ok} -> {gap}")
            trials.append({
                "ticket_id": case["id"],
                "trial": trial_num,
                "expected_tools": case["expected_tools"],
                "tools_called": tools_called,
                "tool_choice_recall": recall,
                "outcome_correct": ok,
                "outcome_vs_trajectory": gap,
                "retry_count": retry_count(res),
                "stopped_by_limit": res.stopped_by_limit,
                "llm_calls": res.llm_calls,
                "final_answer": res.final_answer,
            })
    return trials


def aggregate(trials: list[dict]) -> dict:
    by_ticket = defaultdict(list)
    for t in trials:
        by_ticket[t["ticket_id"]].append(t)

    per_ticket = {}
    for ticket_id, rows in by_ticket.items():
        per_ticket[ticket_id] = {
            "n": len(rows),
            "avg_tool_choice_recall": round(sum(r["tool_choice_recall"] for r in rows) / len(rows), 2),
            "outcome_correct_rate": round(sum(r["outcome_correct"] for r in rows) / len(rows), 2),
            "gap_count": sum(1 for r in rows if r["outcome_vs_trajectory"] == "RIGHT ANSWER, WRONG PATH"),
            "both_wrong_count": sum(1 for r in rows if r["outcome_vs_trajectory"] == "both_wrong"),
            "both_correct_count": sum(1 for r in rows if r["outcome_vs_trajectory"] == "both_correct"),
        }

    gap_cases = [t for t in trials if t["outcome_vs_trajectory"] == "RIGHT ANSWER, WRONG PATH"]
    return {
        "n_trials_per_ticket": N_TRIALS,
        "overall_avg_tool_choice_recall": round(sum(t["tool_choice_recall"] for t in trials) / len(trials), 2),
        "overall_outcome_correct_rate": round(sum(t["outcome_correct"] for t in trials) / len(trials), 2),
        "outcome_vs_trajectory_gap_count": len(gap_cases),
        "outcome_vs_trajectory_gap_rate": round(len(gap_cases) / len(trials), 2),
        "per_ticket": per_ticket,
    }


def main() -> None:
    trials = run_trials()
    summary = aggregate(trials)

    print("\n--- Summary ---")
    print(f"Overall tool-choice recall: {summary['overall_avg_tool_choice_recall']:.0%}")
    print(f"Overall outcome-correct rate: {summary['overall_outcome_correct_rate']:.0%}")
    print(f"Right-answer-wrong-path cases: {summary['outcome_vs_trajectory_gap_count']}/{len(trials)} "
          f"({summary['outcome_vs_trajectory_gap_rate']:.0%})")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"summary": summary, "trials": trials}, indent=2), encoding="utf-8")

    gap_cases = [t for t in trials if t["outcome_vs_trajectory"] == "RIGHT ANSWER, WRONG PATH"]
    md = [
        "# Week 8: Outcome-vs-Trajectory Gap\n",
        f"Each of the 4 tickets from Week 7's race was run {N_TRIALS} times through the fixed "
        f"ReAct agent (same code as `race_agent_vs_workflow.py`, no injection defenses in play "
        f"here — this is purely about trajectory correctness). Repeated trials, not a single run, "
        f"because Week 6 already found this model isn't fully deterministic even at temperature=0.\n",
        "## Summary\n",
        f"- Overall tool-choice recall across all {len(trials)} trials: "
        f"**{summary['overall_avg_tool_choice_recall']:.0%}**\n"
        f"- Overall outcome-correct rate: **{summary['overall_outcome_correct_rate']:.0%}**\n"
        f"- **Right-answer-wrong-path cases: {summary['outcome_vs_trajectory_gap_count']}/{len(trials)} "
        f"({summary['outcome_vs_trajectory_gap_rate']:.0%})** — the agent's final answer passed the "
        f"rule-based outcome check without having called every tool the ticket needed to actually "
        f"know that.\n",
        "| Ticket | Trials | Avg tool recall | Outcome-correct rate | Right-answer-wrong-path | Both wrong |",
        "|---|---|---|---|---|---|",
    ]
    for ticket_id, stats in summary["per_ticket"].items():
        md.append(
            f"| `{ticket_id}` | {stats['n']} | {stats['avg_tool_choice_recall']:.0%} | "
            f"{stats['outcome_correct_rate']:.0%} | {stats['gap_count']} | {stats['both_wrong_count']} |"
        )

    md.append("\n## Evidence: a real right-answer-wrong-path case\n")
    if gap_cases:
        example = gap_cases[0]
        md.append(
            f"`{example['ticket_id']}`, trial {example['trial']}: expected tools "
            f"`{example['expected_tools']}`, agent actually called `{example['tools_called']}` "
            f"(recall={example['tool_choice_recall']}), yet the final answer still passed the "
            f"rule-based outcome check:\n"
        )
        md.append(f"> {example['final_answer'][:600]}\n")
        md.append(
            "This is the agent confidently answering from its own general knowledge/guesswork "
            "instead of the tool data it never actually fetched — it happened to be right this "
            "time, which is exactly why it's dangerous: nothing here would have caught it if it "
            "had guessed wrong.\n"
        )
    else:
        md.append(
            "No right-answer-wrong-path case in this batch of trials — see "
            "`results/agent_failure_modes.md` for one captured in an earlier run and preserved "
            "as evidence, since this failure mode is real but not guaranteed to reproduce on "
            "every batch.\n"
        )

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()
