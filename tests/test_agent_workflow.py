import pytest
from src.rag.agent import (
    FixedSupportWorkflow,
    SupportReActAgent,
    account_status_tool,
    error_lookup_tool,
    validate_output,
    _wrap_untrusted,
)

def test_error_lookup_tool():
    res = error_lookup_tool("NB-AUTH-410")
    assert "Password reset link expired" in res
    assert "NB-AUTH-410" in res or "30" in res

def test_account_status_tool():
    res = account_status_tool("maria@startup.io")
    assert "locked" in res
    assert "pro" in res

def test_fixed_workflow_execution():
    wf = FixedSupportWorkflow()
    ticket = "I am maria@startup.io with error NB-AUTH-500"
    res = wf.execute(ticket)
    assert res.llm_calls == 1
    assert len(res.steps) >= 2
    assert res.final_answer

def test_agent_tool_descriptions():
    agent = SupportReActAgent()
    desc = agent._render_tool_descriptions()
    assert "kb_search" in desc
    assert "error_lookup" in desc
    assert "account_status" in desc


# --- Week 8: stop-safety, least-privilege tool scoping, prompt-injection defenses ---
# These use a fake LLM / call internal methods directly so they're deterministic and make no
# network calls — the real end-to-end behavior is exercised by
# src/scripts/{trajectory_eval,prompt_injection_test}.py against the live model instead.

class _NeverFinishesLLM:
    """Always returns a valid Action, never a Final Answer — for testing that the step-limit
    actually engages, without depending on a real model's behavior to reach it."""
    def invoke(self, prompt, stop=None):
        class _Msg:
            content = "Thought: still working\nAction: error_lookup\nAction Input: NB-AUTH-410"
        return _Msg()


def test_agent_stops_safely_at_max_steps():
    agent = SupportReActAgent(max_steps=3, timeout_sec=40.0)
    agent.llm = _NeverFinishesLLM()
    res = agent.solve("a ticket with no email or error code in it")
    assert res.stopped_by_limit is True
    assert len(res.steps) == 3
    assert all(s.kind == "action" and s.action == "error_lookup" for s in res.steps)


def test_run_tool_blocks_out_of_scope_account_lookup():
    agent = SupportReActAgent(enforce_least_privilege=True)
    obs = agent._run_tool("account_status", "alex@company.com", authorized_email="maria@startup.io")
    assert "access denied" in obs.lower()


def test_run_tool_allows_authorized_account_lookup():
    agent = SupportReActAgent(enforce_least_privilege=True)
    obs = agent._run_tool("account_status", "maria@startup.io", authorized_email="maria@startup.io")
    assert "locked" in obs.lower()


def test_run_tool_least_privilege_disabled_allows_any_lookup():
    agent = SupportReActAgent(enforce_least_privilege=False)
    obs = agent._run_tool("account_status", "alex@company.com", authorized_email="maria@startup.io")
    assert "access denied" not in obs.lower()


def test_wrap_untrusted_delimits_tool_output():
    wrapped = _wrap_untrusted("account_status", "some tool data")
    assert wrapped.startswith('<tool_output source="account_status">')
    assert "some tool data" in wrapped
    assert wrapped.strip().endswith("</tool_output>")


def test_validate_output_redacts_out_of_scope_email():
    text = "By the way, alex@company.com's account is in good standing too."
    redacted, leaked = validate_output(text, "maria@startup.io")
    assert leaked is True
    assert "alex@company.com" not in redacted
    assert "[redacted" in redacted


def test_validate_output_leaves_authorized_email_alone():
    text = "maria@startup.io's account is locked."
    redacted, leaked = validate_output(text, "maria@startup.io")
    assert leaked is False
    assert redacted == text
