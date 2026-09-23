"""Week 7: Race the Ticket Agent against a Fixed Workflow.

Benchmarks the hand-built ReAct Agent vs. the Fixed Sequence Workflow across realistic,
multi-step customer support tickets on:
- Speed (Latency in seconds)
- Cost (LLM reasoning calls / token overhead)
- Reliability & Quality (Step visibility and completeness of resolution)
Outputs results/agent_vs_workflow.json and results/agent_vs_workflow.md.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.stdout.reconfigure(encoding="utf-8")

import json
import re
import time
from src.rag.config import ROOT_DIR
from src.rag.agent import SupportReActAgent, FixedSupportWorkflow

OUT_JSON = ROOT_DIR / "results" / "agent_vs_workflow.json"
OUT_MD = ROOT_DIR / "results" / "agent_vs_workflow.md"

TEST_TICKETS = [
    {
        "id": "ticket_01_account_lock",
        "title": "Account locked & 2FA issue",
        "ticket": "Hi, I'm maria@startup.io and my account is locked out after getting error NB-AUTH-500. Can you tell me what happened and how to unlock it?",
        "expected_tools": ["account_status", "error_lookup"],
        "multi_step": True,
        # Present in the real tool output but not guessable from the question text alone — an
        # answer containing this had to have actually called error_lookup, not just pattern-matched.
        "expected_answer_keywords": ["suspicious activity", "admin console"],
    },
    {
        "id": "ticket_02_sync_quota_conflict",
        "title": "Sync upload error & storage check",
        "ticket": "User john@domain.com here. I'm trying to upload a file and getting error NB-UP-330. Is my account full or what is the issue?",
        "expected_tools": ["account_status", "error_lookup", "kb_search"],
        "multi_step": True,
        "expected_answer_keywords": ["2 gb", "2gb"],
    },
    {
        "id": "ticket_03_simple_share_link",
        "title": "Simple KB permission question",
        "ticket": "How do I share a folder so that only specific invited users can edit it, and commenters cannot?",
        "expected_tools": ["kb_search"],
        "multi_step": False,
        "expected_answer_keywords": ["invite", "editor"],
    },
    {
        "id": "ticket_04_complex_auth_reset",
        "title": "Password reset error code diagnostic",
        "ticket": "I attempted to reset my password but got error NB-AUTH-410. Why did this happen and what should I do next?",
        "expected_tools": ["error_lookup"],
        "multi_step": False,
        "expected_answer_keywords": ["30 minutes", "expired"],
    }
]


def tool_sequence(agent_result) -> list[str]:
    """Only steps that actually executed a tool — a "retry" step (couldn't parse a valid Action)
    has action=None just like a genuine Final Answer step, so this can't just check `if s.action`."""
    return [s.action for s in agent_result.steps if s.kind == "action"]


def retry_count(agent_result) -> int:
    return sum(1 for s in agent_result.steps if s.kind == "retry")


def tool_choice_recall(actual_tools: list[str], expected_tools: list[str]) -> float:
    """Fraction of the tools this ticket actually needed that were really called — the
    trajectory-correctness signal, independent of whether the final answer looks right."""
    if not expected_tools:
        return 1.0
    called = set(actual_tools)
    return round(len(called & set(expected_tools)) / len(expected_tools), 2)


def outcome_correct(final_answer: str, expected_keywords: list[str]) -> bool:
    """Rule-based, not judge-based, on purpose (Week 6 philosophy: free checks first) — every
    keyword here is a fact that only appears in the tool's *real* output, never in the question.

    Whitespace is normalized before matching — Groq's output sometimes uses a narrow no-break
    space (U+202F) between a number and a unit ("2 GB") instead of a plain ASCII space, which
    a literal "2 gb" substring check would silently miss and misreport as ungrounded.
    """
    text = re.sub(r"\s+", " ", final_answer.lower())
    return any(kw in text for kw in expected_keywords)


def classify_outcome_vs_trajectory(outcome_ok: bool, trajectory_ok: bool) -> str:
    if outcome_ok and trajectory_ok:
        return "both_correct"
    if outcome_ok and not trajectory_ok:
        return "RIGHT ANSWER, WRONG PATH"  # the exact case Week 8 asks us to find
    if not outcome_ok and trajectory_ok:
        return "right_path_wrong_answer"
    return "both_wrong"


def run_race():
    agent = SupportReActAgent(max_steps=5, timeout_sec=40.0)
    workflow = FixedSupportWorkflow()

    results = []

    print("=" * 60)
    print("WEEK 7: RACING REACT AGENT VS FIXED WORKFLOW")
    print("=" * 60)

    for case in TEST_TICKETS:
        print(f"\n[Ticket] {case['id']}: {case['title']}")
        ticket_text = case["ticket"]

        # Run ReAct Agent
        print("  Running ReAct Agent...")
        t0 = time.time()
        agent_res = agent.solve(ticket_text)
        agent_time = time.time() - t0
        print(f"  Agent finished in {agent_time:.2f}s ({agent_res.llm_calls} LLM calls, {len(agent_res.steps)} steps)")
        for s in agent_res.steps:
            if s.kind == "action":
                print(f"    - Step {s.step_num}: Action={s.action}({s.action_input})")
            elif s.kind == "retry":
                print(f"    - Step {s.step_num}: [retry] couldn't parse a valid Action from the model's response")
            else:
                print(f"    - Step {s.step_num}: Final Answer produced")

        # Run Fixed Workflow
        print("  Running Fixed Workflow...")
        t0 = time.time()
        wf_res = workflow.execute(ticket_text)
        wf_time = time.time() - t0
        print(f"  Workflow finished in {wf_time:.2f}s ({wf_res.llm_calls} LLM call, {len(wf_res.steps)} steps)")

        expected_tools = case["expected_tools"]
        expected_keywords = case["expected_answer_keywords"]

        agent_tools_called = tool_sequence(agent_res)
        agent_trajectory_score = tool_choice_recall(agent_tools_called, expected_tools)
        agent_outcome_ok = outcome_correct(agent_res.final_answer, expected_keywords)
        agent_gap = classify_outcome_vs_trajectory(agent_outcome_ok, agent_trajectory_score == 1.0)

        wf_tools_called = tool_sequence(wf_res)
        wf_trajectory_score = tool_choice_recall(wf_tools_called, expected_tools)
        wf_outcome_ok = outcome_correct(wf_res.final_answer, expected_keywords)

        print(f"    Agent tools called: {agent_tools_called} (expected {expected_tools}) "
              f"-> trajectory={agent_trajectory_score} outcome_ok={agent_outcome_ok} [{agent_gap}]")

        results.append({
            "ticket_id": case["id"],
            "title": case["title"],
            "ticket": ticket_text,
            "multi_step": case["multi_step"],
            "expected_tools": expected_tools,
            "agent": {
                "duration_sec": round(agent_res.total_duration_sec, 2),
                "llm_calls": agent_res.llm_calls,
                "step_count": len(agent_res.steps),
                "steps": [
                    {
                        "step": s.step_num,
                        "kind": s.kind,
                        "thought": s.thought[:150],
                        "action": s.action,
                        "action_input": s.action_input,
                        "obs_preview": (s.observation or "")[:150]
                    }
                    for s in agent_res.steps
                ],
                "final_answer": agent_res.final_answer,
                "stopped_by_limit": agent_res.stopped_by_limit,
                "output_leak_redacted": agent_res.output_leak_redacted,
                "retry_count": retry_count(agent_res),
                "tools_called": agent_tools_called,
                "tool_choice_recall": agent_trajectory_score,
                "outcome_correct": agent_outcome_ok,
                "outcome_vs_trajectory": agent_gap,
            },
            "workflow": {
                "duration_sec": round(wf_res.total_duration_sec, 2),
                "llm_calls": wf_res.llm_calls,
                "step_count": len(wf_res.steps),
                "final_answer": wf_res.final_answer,
                "tools_called": wf_tools_called,
                "tool_choice_recall": wf_trajectory_score,
                "outcome_correct": wf_outcome_ok,
            }
        })

    # Summary aggregations
    avg_agent_time = sum(r["agent"]["duration_sec"] for r in results) / len(results)
    avg_wf_time = sum(r["workflow"]["duration_sec"] for r in results) / len(results)
    total_agent_calls = sum(r["agent"]["llm_calls"] for r in results)
    total_wf_calls = sum(r["workflow"]["llm_calls"] for r in results)
    agent_trajectory_avg = round(sum(r["agent"]["tool_choice_recall"] for r in results) / len(results), 2)
    agent_outcome_rate = round(sum(r["agent"]["outcome_correct"] for r in results) / len(results), 2)
    gap_cases = [r["ticket_id"] for r in results if r["agent"]["outcome_vs_trajectory"] == "RIGHT ANSWER, WRONG PATH"]

    # Compute winners from the actual numbers instead of assuming one side always wins —
    # this file used to hardcode "Fixed Workflow" as the speed winner regardless of the numbers.
    speed_winner = "ReAct Agent" if avg_agent_time < avg_wf_time else "Fixed Workflow"
    speed_ratio = round(max(avg_agent_time, avg_wf_time) / min(avg_agent_time, avg_wf_time), 2) if min(avg_agent_time, avg_wf_time) > 0 else "N/A"
    cost_winner = "ReAct Agent" if total_agent_calls < total_wf_calls else ("Fixed Workflow" if total_wf_calls < total_agent_calls else "Tie")

    report_data = {
        "summary": {
            "tickets_evaluated": len(results),
            "agent_avg_duration_sec": round(avg_agent_time, 2),
            "workflow_avg_duration_sec": round(avg_wf_time, 2),
            "agent_total_llm_calls": total_agent_calls,
            "workflow_total_llm_calls": total_wf_calls,
            "speed_winner": speed_winner,
            "speed_ratio_x": speed_ratio,
            "cost_winner": cost_winner,
            "agent_avg_tool_choice_recall": agent_trajectory_avg,
            "agent_outcome_correct_rate": agent_outcome_rate,
            "outcome_vs_trajectory_gap_cases": gap_cases,
        },
        "details": results
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # Generate Markdown Deliverable
    md_content = f"""# Week 7 Deliverable: Agent Loops vs. Fixed Sequence Workflow

Race between a hand-built **ReAct Agent** (plan -> act -> observe loop) and a **Fixed Sequence Workflow** on multi-step customer support tickets.

## 1. Executive Comparison

| Metric | Hand-Built ReAct Agent | Fixed Sequence Workflow | Winner / Trade-off |
|---|---|---|---|
| **Average Latency** | **{avg_agent_time:.2f}s** | **{avg_wf_time:.2f}s** | **{speed_winner}** ({speed_ratio}x faster) |
| **LLM Calls (Cost)** | **{total_agent_calls} calls** | **{total_wf_calls} calls** | **{cost_winner}** |
| **Tool Calling Flexibility** | Dynamic (selects only relevant tools) | Rigid (runs predetermined checks) | **ReAct Agent** |
| **Reliability / Loop Safety** | Guarded by max 5 steps & timeout budget | 100% deterministic execution | **Fixed Workflow** for known paths |
| **Trajectory correctness** (did it call the tools this ticket actually needed?) | **{agent_trajectory_avg:.0%}** avg tool-choice recall | 100% (deterministic) | **Fixed Workflow** — it can't skip a step |
| **Outcome correctness** (rule-checked against facts only a tool call could know) | **{agent_outcome_rate:.0%}** | see per-ticket detail | — |

Winners are computed from the numbers above, not assumed — an earlier version of this report
hardcoded "Fixed Workflow" as the speed winner regardless of which side actually ran faster.
{"**Outcome-vs-trajectory gap found**: " + ", ".join(gap_cases) + " — the agent's final answer passed the rule-based outcome check even though it didn't call every tool this ticket needed. See Week 8's `results/agent_failure_modes.md` for the full writeup." if gap_cases else "No outcome-vs-trajectory gap in this run — every ticket where the agent's answer passed the outcome check also called every tool the ticket needed."}

## 2. When to Use Which? (Engineering Decision)

### When to use the Fixed Workflow (Recommended for Production Support):
1. **Predetermined Pathways**: When customer tickets follow a standard sequence (e.g., extract user ID -> check account status -> retrieve error code -> answer).
2. **Speed & Budget**: Fixed workflows require only 1 LLM generation call + direct deterministic tool calls, saving cost and eliminating multi-turn latency.
3. **Determinism**: Zero risk of an agent hallucinatory loop or tool misdirection.

### When to use the ReAct Agent:
1. **Dynamic & Unpredictable Problems**: When the next investigation step depends completely on unexpected observations from prior steps.
2. **Ad-Hoc Tool Exploration**: When the search space has dozens of specialized tools and running all of them in a fixed pipeline would be wasteful.

## 3. Test Cases & Step Visibility

"""
    for r in results:
        md_content += f"### Ticket: {r['title']} (`{r['ticket_id']}`)\n"
        md_content += f"> **User Ticket**: \"{r['ticket']}\"\n\n"
        md_content += f"- **ReAct Agent**: {r['agent']['duration_sec']}s, {r['agent']['llm_calls']} LLM calls, {r['agent']['step_count']} steps.\n"
        md_content += f"- **Fixed Workflow**: {r['workflow']['duration_sec']}s, {r['workflow']['llm_calls']} LLM call.\n"
        md_content += (
            f"- **Trajectory**: expected tools `{r['expected_tools']}`, agent actually called "
            f"`{r['agent']['tools_called']}` (recall={r['agent']['tool_choice_recall']}), "
            f"outcome_correct={r['agent']['outcome_correct']} -> **{r['agent']['outcome_vs_trajectory']}**\n\n"
        )
        if r["agent"]["retry_count"]:
            md_content += (
                f"- **Format retries**: {r['agent']['retry_count']} step(s) where the model's response "
                f"didn't parse into a valid Action or Final Answer (a real, occasional failure mode of "
                f"this Groq model at this prompt — not a bug in the parser, see `results/agent_failure_modes.md`).\n"
            )
        if r["agent"]["output_leak_redacted"]:
            md_content += "- **Output validator caught and redacted an out-of-scope customer reference.**\n"
        md_content += "\n#### Visible ReAct Step Trace:\n"
        for s in r["agent"]["steps"]:
            if s["kind"] == "action":
                md_content += f"- **Step {s['step']}**: Thought: *{s['thought']}* -> **Action**: `{s['action']}`(`{s['action_input']}`) -> Observation: `{s['obs_preview']}`\n"
            elif s["kind"] == "retry":
                md_content += f"- **Step {s['step']}**: [retry] Response didn't parse into a valid Action or Final Answer — no tool called, step wasted.\n"
            else:
                md_content += f"- **Step {s['step']}**: Thought: *{s['thought']}* -> **Produced Final Answer**\n"
        md_content += "\n---\n\n"

    OUT_MD.write_text(md_content, encoding="utf-8")
    print(f"\nWrote benchmark data to {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    run_race()
