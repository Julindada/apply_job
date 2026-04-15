"""
Unit tests for nodes/llm_score.py
"""

import json
from unittest.mock import MagicMock, patch

from apply_job.nodes.llm_score import llm_score_node

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
    "filtered_jobs": [{
        "id": "1",
        "title": "Backend Engineer",
        "companyName": "Acme",
        "link": "https://linkedin.com/jobs/1",
        "descriptionText": "Java Spring Boot microservices.",
    }],
    "resume_path": "/fake/resume.pdf",
}


def _run(jobs, scores, **state_overrides):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=json.dumps(scores))

    state = {**_BASE_STATE, "filtered_jobs": jobs, **state_overrides}

    with patch("apply_job.nodes.llm_score._read_resume", return_value="Java developer"), \
         patch("apply_job.nodes.llm_score.ChatOpenAI", return_value=mock_llm):
        return llm_score_node(state)


def test_empty_filtered_jobs_skips_llm():
    result = llm_score_node({**_BASE_STATE, "filtered_jobs": []})
    assert result == {"filtered_jobs": [], "unsuitable_jobs": []}


def test_suitable_job_goes_to_filtered_jobs():
    result = _run(_BASE_STATE["filtered_jobs"], [_SCORE_SUITABLE])
    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["id"] == "1"
    assert result["unsuitable_jobs"] == []


def test_unsuitable_job_goes_to_unsuitable_jobs():
    score = {**_SCORE_SUITABLE, "classification": "unsuitable"}
    result = _run(_BASE_STATE["filtered_jobs"], [score])
    assert result["filtered_jobs"] == []
    assert len(result["unsuitable_jobs"]) == 1


def test_pending_job_goes_to_filtered_jobs():
    score = {**_SCORE_SUITABLE, "classification": "pending"}
    result = _run(_BASE_STATE["filtered_jobs"], [score])
    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["classification"] == "pending"
    assert result["unsuitable_jobs"] == []


def test_mixed_classifications_split_correctly():
    jobs = [
        {**_BASE_STATE["filtered_jobs"][0], "id": "1"},
        {**_BASE_STATE["filtered_jobs"][0], "id": "2"},
        {**_BASE_STATE["filtered_jobs"][0], "id": "3"},
    ]
    scores = [
        {**_SCORE_SUITABLE, "id": "1", "classification": "suitable"},
        {**_SCORE_SUITABLE, "id": "2", "classification": "unsuitable"},
        {**_SCORE_SUITABLE, "id": "3", "classification": "pending"},
    ]
    result = _run(jobs, scores)
    assert {j["id"] for j in result["filtered_jobs"]} == {"1", "3"}
    assert {j["id"] for j in result["unsuitable_jobs"]} == {"2"}


def test_score_fields_merged_into_output_job():
    result = _run(_BASE_STATE["filtered_jobs"], [_SCORE_SUITABLE])
    out = result["filtered_jobs"][0]
    for field in ("tech_stack", "experience_level", "overall", "summary"):
        assert field in out
