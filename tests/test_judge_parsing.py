from src.rag.chain import _parse_judge_json


def test_parses_plain_json():
    result = _parse_judge_json('{"faithfulness": 5, "relevancy": 4}')
    assert result == {"faithfulness": 5, "relevancy": 4, "raw": '{"faithfulness": 5, "relevancy": 4}'}


def test_strips_markdown_code_fence():
    raw = '```json\n{"faithfulness": 3, "relevancy": 2}\n```'
    result = _parse_judge_json(raw)
    assert result["faithfulness"] == 3
    assert result["relevancy"] == 2


def test_returns_nones_on_unparseable_output():
    result = _parse_judge_json("I refuse to output JSON today.")
    assert result["faithfulness"] is None
    assert result["relevancy"] is None
    assert result["raw"] == "I refuse to output JSON today."
