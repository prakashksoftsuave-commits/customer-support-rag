from src.rag.agent import AgentResult, AgentStep
from src.scripts.race_agent_vs_workflow import (
    classify_outcome_vs_trajectory,
    outcome_correct,
    retry_count,
    tool_choice_recall,
    tool_sequence,
)


def _result(steps: list[AgentStep]) -> AgentResult:
    return AgentResult(final_answer="x", steps=steps, total_duration_sec=1.0, llm_calls=len(steps))


def test_tool_sequence_excludes_retries_and_final_answer():
    # A "retry" step (couldn't parse a valid Action) has action=None just like a genuine Final
    # Answer step — this is exactly the ambiguity that used to get retries mislabeled as
    # "Final Answer produced" in reports before AgentStep.kind was added.
    steps = [
        AgentStep(1, "t", "account_status", "a@b.com", "obs", kind="action"),
        AgentStep(2, "t", None, None, None, kind="retry"),
        AgentStep(3, "t", "error_lookup", "NB-1", "obs", kind="action"),
        AgentStep(4, "t", None, None, None, kind="final_answer"),
    ]
    res = _result(steps)
    assert tool_sequence(res) == ["account_status", "error_lookup"]
    assert retry_count(res) == 1


def test_tool_choice_recall():
    assert tool_choice_recall(["a", "b"], ["a", "b"]) == 1.0
    assert tool_choice_recall(["a"], ["a", "b"]) == 0.5
    assert tool_choice_recall([], ["a"]) == 0.0
    assert tool_choice_recall(["a", "a", "a"], ["a"]) == 1.0  # repeats don't inflate past 1.0
    assert tool_choice_recall(["a"], []) == 1.0  # nothing expected -> vacuously satisfied


def test_outcome_correct_normalizes_narrow_nbsp():
    # Groq's output sometimes uses a narrow no-break space (U+202F) between a number and a unit
    # instead of a plain ASCII space — a literal "2 gb" substring check would miss "2 gb" and
    # misreport a genuinely grounded answer as ungrounded.
    assert outcome_correct("the limit is 2 GB total", ["2 gb"]) is True
    assert outcome_correct("no relevant figure here", ["2 gb"]) is False


def test_classify_outcome_vs_trajectory():
    assert classify_outcome_vs_trajectory(True, True) == "both_correct"
    assert classify_outcome_vs_trajectory(True, False) == "RIGHT ANSWER, WRONG PATH"
    assert classify_outcome_vs_trajectory(False, True) == "right_path_wrong_answer"
    assert classify_outcome_vs_trajectory(False, False) == "both_wrong"
