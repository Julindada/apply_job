"""
Unit tests for nodes/review_pending_jobs.py
"""

from unittest.mock import patch

from apply_job.nodes.review_pending_jobs import review_pending_jobs_node

_SUITABLE_JOB = {"id": "1", "title": "Backend Engineer", "classification": "suitable"}
_PENDING_JOB  = {"id": "2", "title": "Java Developer",   "classification": "pending"}


def _state(filtered_jobs, unsuitable_jobs=None):
    return {
        "filtered_jobs":  filtered_jobs,
        "unsuitable_jobs": unsuitable_jobs or [],
    }


def test_no_pending_jobs_returns_empty_update():
    """Suitable-only filtered_jobs: node returns {} and interrupt is never called."""
    with patch("apply_job.nodes.review_pending_jobs.interrupt") as mock_interrupt:
        result = review_pending_jobs_node(_state([_SUITABLE_JOB]))

    assert result == {}
    mock_interrupt.assert_not_called()


def test_pending_marked_suitable_moves_to_filtered_jobs():
    with patch("apply_job.nodes.review_pending_jobs.interrupt", return_value="s"):
        result = review_pending_jobs_node(_state([_PENDING_JOB]))

    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["classification"] == "suitable"
    assert result["unsuitable_jobs"] == []


def test_pending_marked_unsuitable_moves_to_unsuitable_jobs():
    with patch("apply_job.nodes.review_pending_jobs.interrupt", return_value="u"):
        result = review_pending_jobs_node(_state([_PENDING_JOB]))

    assert result["filtered_jobs"] == []
    assert len(result["unsuitable_jobs"]) == 1
    assert result["unsuitable_jobs"][0]["classification"] == "unsuitable"


def test_suitable_jobs_pass_through_unchanged():
    """Suitable jobs must not be touched when there are also pending jobs."""
    with patch("apply_job.nodes.review_pending_jobs.interrupt", return_value="u"):
        result = review_pending_jobs_node(_state([_SUITABLE_JOB, _PENDING_JOB]))

    assert any(j["id"] == "1" for j in result["filtered_jobs"])


def test_existing_unsuitable_jobs_are_preserved():
    """Jobs already in unsuitable_jobs must not be lost."""
    existing = {"id": "99", "title": "Frontend", "classification": "unsuitable"}
    with patch("apply_job.nodes.review_pending_jobs.interrupt", return_value="u"):
        result = review_pending_jobs_node(_state([_PENDING_JOB], unsuitable_jobs=[existing]))

    ids = {j["id"] for j in result["unsuitable_jobs"]}
    assert "99" in ids
    assert "2" in ids
