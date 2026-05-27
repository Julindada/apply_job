"""
Unit tests for nodes/rule_filter.py
"""

from unittest.mock import patch, MagicMock

from apply_job.nodes.rule_filter import rule_filter_node

_JOB = {
    "id": "1",
    "title": "Backend Engineer",
    "companyName": "Acme",
    "link": "https://linkedin.com/jobs/1",
    "descriptionText": "Java Spring Boot microservices.",
}

_BASE_STATE = {
    "raw_jobs": [_JOB],
    "resume_path": "/fake/resume.pdf",
    "excluded_files": [],
}


def test_empty_raw_jobs_returns_empty_filtered():
    result = rule_filter_node({**_BASE_STATE, "raw_jobs": []})
    assert result == {"filtered_jobs": []}


def test_single_job_passed_through():
    with patch("apply_job.nodes.rule_filter._load_excluded_ids", return_value=set()), \
         patch("apply_job.nodes.rule_filter._load_rejected_companies", return_value=set()), \
         patch("apply_job.nodes.rule_filter._should_keep", return_value=True):
        result = rule_filter_node(_BASE_STATE)
    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["id"] == "1"


def test_excluded_job_not_in_output():
    with patch("apply_job.nodes.rule_filter._load_excluded_ids", return_value=set()), \
         patch("apply_job.nodes.rule_filter._load_rejected_companies", return_value=set()), \
         patch("apply_job.nodes.rule_filter._should_keep", return_value=False):
        result = rule_filter_node(_BASE_STATE)
    assert result["filtered_jobs"] == []
