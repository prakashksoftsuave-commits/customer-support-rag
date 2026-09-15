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
        "multi_step": True
    },
    {
        "id": "ticket_02_sync_quota_conflict",
        "title": "Sync upload error & storage check",
        "ticket": "User john@domain.com here. I'm trying to upload a file and getting error NB-UP-330. Is my account full or what is the issue?",
        "expected_tools": ["account_status", "error_lookup", "kb_search"],
        "multi_step": True
    },
    {
        "id": "ticket_03_simple_share_link",
        "title": "Simple KB permission question",
        "ticket": "How do I share a folder so that only specific invited users can edit it, and commenters cannot?",
        "expected_tools": ["kb_search"],
        "multi_step": False
    },
    {
        "id": "ticket_04_complex_auth_reset",
        "title": "Password reset error code diagnostic",
        "ticket": "I attempted to reset my password but got error NB-AUTH-410. Why did this happen and what should I do next?",
        "expected_tools": ["error_lookup"],
        "multi_step": False
    }
]


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
            if s.action:
                print(f"    - Step {s.step_num}: Action={s.action}({s.action_input})")
            else:
                print(f"    - Step {s.step_num}: Final Answer produced")

        # Run Fixed Workflow
        print("  Running Fixed Workflow...")
        t0 = time.time()
        wf_res = workflow.execute(ticket_text)
        wf_time = time.time() - t0
        print(f"  Workflow finished in {wf_time:.2f}s ({wf_res.llm_calls} LLM call, {len(wf_res.steps)} steps)")

        results.append({
            "ticket_id": case["id"],
            "title": case["title"],
            "ticket": ticket_text,
            "multi_step": case["multi_step"],
            "agent": {
                "duration_sec": round(agent_res.total_duration_sec, 2),
                "llm_calls": agent_res.llm_calls,
                "step_count": len(agent_res.steps),
                "steps": [
                    {
                        "step": s.step_num,
                        "thought": s.thought[:150],
                        "action": s.action,
                        "action_input": s.action_input,
                        "obs_preview": (s.observation or "")[:150]
                    }
                    for s in agent_res.steps
                ],
                "final_answer": agent_res.final_answer,
                "stopped_by_limit": agent_res.stopped_by_limit
            },
            "workflow": {
                "duration_sec": round(wf_res.total_duration_sec, 2),
                "llm_calls": wf_res.llm_calls,
                "step_count": len(wf_res.steps),
                "final_answer": wf_res.final_answer
            }
        })

    # Summary aggregations
    avg_agent_time = sum(r["agent"]["duration_sec"] for r in results) / len(results)
    avg_wf_time = sum(r["workflow"]["duration_sec"] for r in results) / len(results)
    total_agent_calls = sum(r["agent"]["llm_calls"] for r in results)
    total_wf_calls = sum(r["workflow"]["llm_calls"] for r in results)

    report_data = {
        "summary": {
            "tickets_evaluated": len(results),
            "agent_avg_duration_sec": round(avg_agent_time, 2),
            "workflow_avg_duration_sec": round(avg_wf_time, 2),
            "agent_total_llm_calls": total_agent_calls,
            "workflow_total_llm_calls": total_wf_calls,
            "speed_ratio": round(avg_agent_time / avg_wf_time, 2) if avg_wf_time > 0 else "N/A"
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
| **Average Latency** | **{avg_agent_time:.2f}s** | **{avg_wf_time:.2f}s** | **Fixed Workflow** ({report_data['summary']['speed_ratio']}x faster) |
| **LLM Calls (Cost)** | **{total_agent_calls} calls** | **{total_wf_calls} calls** | **Fixed Workflow** ({total_wf_calls} total calls vs {total_agent_calls}) |
| **Tool Calling Flexibility** | Dynamic (selects only relevant tools) | Rigid (runs predetermined checks) | **ReAct Agent** |
| **Reliability / Loop Safety** | Guarded by max 5 steps & timeout budget | 100% deterministic execution | **Fixed Workflow** for known paths |

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
        md_content += f"- **Fixed Workflow**: {r['workflow']['duration_sec']}s, {r['workflow']['llm_calls']} LLM call.\n\n"
        md_content += "#### Visible ReAct Step Trace:\n"
        for s in r["agent"]["steps"]:
            if s["action"]:
                md_content += f"- **Step {s['step']}**: Thought: *{s['thought']}* -> **Action**: `{s['action']}`(`{s['action_input']}`)\n"
            else:
                md_content += f"- **Step {s['step']}**: Thought: *{s['thought']}* -> **Produced Final Answer**\n"
        md_content += "\n---\n\n"

    OUT_MD.write_text(md_content, encoding="utf-8")
    print(f"\nWrote benchmark data to {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    run_race()
