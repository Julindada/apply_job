"""
Unit tests for nodes/filter_jobs.py

LangChain tools are Pydantic frozen models — patch.object cannot replace
their inherited methods. Instead we patch the name in the node's own
module namespace, replacing the whole tool object with a MagicMock.
"""

import json
from unittest.mock import MagicMock, patch

from apply_job.nodes.filter_jobs import filter_jobs_node

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_JOB = {
    "id": "1",
    "title": "Backend Engineer",
    "companyName": "Acme",
    "link": "https://linkedin.com/jobs/1",
    "descriptionText": "Java Spring Boot microservices.",
}

_SCORE_SUITABLE = {
    "id": "1",
    "title": "Backend Engineer",
    "companyName": "Acme",
    "link": "https://linkedin.com/jobs/1",
    "tech_stack": 8,
    "experience_level": 7,
    "language_requirements": 9,
    "domain_fit": 8,
    "overall": 8,
    "classification": "suitable",
    "summary": "Java主语言，符合JVM要求。",
}

_BASE_STATE = {
    "raw_jobs": [_JOB],
    "data_dir": "data",
    "resume_path": "/fake/resume.pdf",
    "excluded_files": [],
}


def _run(jobs_after_rules, scores, **state_overrides):
    """Run filter_jobs_node with both the rule tool and LLM mocked."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = jobs_after_rules

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=json.dumps(scores))

    state = {**_BASE_STATE, **state_overrides}

    with patch("apply_job.nodes.filter_jobs.filter_jobs", new=mock_tool), \
         patch("apply_job.nodes.filter_jobs._read_resume", return_value="Java developer"), \
         patch("apply_job.nodes.filter_jobs.ChatOpenAI", return_value=mock_llm):
        return filter_jobs_node(state)


# ---------------------------------------------------------------------------
# Node tests — stage 1: rule-based filter
# ---------------------------------------------------------------------------


def test_empty_raw_jobs_skips_llm():
    """No jobs → both output lists are empty and LLM is never called."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = []

    with patch("apply_job.nodes.filter_jobs.filter_jobs", new=mock_tool), \
         patch("apply_job.nodes.filter_jobs.ChatOpenAI") as mock_llm_cls:
        result = filter_jobs_node({**_BASE_STATE, "raw_jobs": []})

    assert result == {"filtered_jobs": [], "unsuitable_jobs": []}
    mock_llm_cls.assert_not_called()


def test_all_jobs_excluded_by_rules_skips_llm():
    """If the rule tool drops every job, the LLM is never called."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = []

    with patch("apply_job.nodes.filter_jobs.filter_jobs", new=mock_tool), \
         patch("apply_job.nodes.filter_jobs.ChatOpenAI") as mock_llm_cls:
        result = filter_jobs_node(_BASE_STATE)

    assert result["filtered_jobs"] == []
    assert result["unsuitable_jobs"] == []
    mock_llm_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Node tests — stage 2: LLM classification
# ---------------------------------------------------------------------------


def test_suitable_job_goes_to_filtered_jobs():
    result = _run([_JOB], [_SCORE_SUITABLE])

    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["id"] == "1"
    assert result["unsuitable_jobs"] == []


def test_unsuitable_job_goes_to_unsuitable_jobs():
    score = {**_SCORE_SUITABLE, "classification": "unsuitable"}
    result = _run([_JOB], [score])

    assert result["filtered_jobs"] == []
    assert len(result["unsuitable_jobs"]) == 1


def test_pending_job_goes_to_filtered_jobs():
    score = {**_SCORE_SUITABLE, "classification": "pending"}
    result = _run([_JOB], [score])

    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["classification"] == "pending"
    assert result["unsuitable_jobs"] == []


def test_mixed_classifications_split_correctly():
    job2 = {**_JOB, "id": "2"}
    job3 = {**_JOB, "id": "3"}
    scores = [
        {**_SCORE_SUITABLE, "id": "1", "classification": "suitable"},
        {**_SCORE_SUITABLE, "id": "2", "classification": "unsuitable"},
        {**_SCORE_SUITABLE, "id": "3", "classification": "pending"},
    ]
    result = _run([_JOB, job2, job3], scores)

    assert {j["id"] for j in result["filtered_jobs"]} == {"1", "3"}
    assert {j["id"] for j in result["unsuitable_jobs"]} == {"2"}


def test_score_fields_merged_into_output_job():
    """LLM score fields must be present on each output job dict."""
    result = _run([_JOB], [_SCORE_SUITABLE])

    out = result["filtered_jobs"][0]
    for field in ("tech_stack", "experience_level", "overall", "summary"):
        assert field in out
