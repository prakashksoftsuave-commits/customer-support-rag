import pytest
from src.rag.agent import SupportReActAgent, FixedSupportWorkflow, error_lookup_tool, account_status_tool

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
