"""
Unit tests for nodes/company_dedup.py
"""

from apply_job.nodes.company_dedup import company_dedup_node


def test_no_duplicates_all_returned():
    jobs = [
        {"id": "1", "companyName": "A", "overall": 8},
        {"id": "2", "companyName": "B", "overall": 7},
    ]
    result = company_dedup_node({"filtered_jobs": jobs})
    assert len(result["filtered_jobs"]) == 2


def test_duplicate_company_keeps_highest_score():
    jobs = [
        {"id": "1", "companyName": "Acme", "overall": 5},
        {"id": "2", "companyName": "Acme", "overall": 9},
    ]
    result = company_dedup_node({"filtered_jobs": jobs})
    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["id"] == "2"


def test_duplicate_company_equal_scores_keeps_first():
    jobs = [
        {"id": "1", "companyName": "Acme", "overall": 8},
        {"id": "2", "companyName": "Acme", "overall": 8},
    ]
    result = company_dedup_node({"filtered_jobs": jobs})
    assert len(result["filtered_jobs"]) == 1
    assert result["filtered_jobs"][0]["id"] == "1"


def test_empty_filtered_jobs():
    result = company_dedup_node({"filtered_jobs": []})
    assert result["filtered_jobs"] == []


def test_not_added_to_unsuitable():
    """Duplicates are dropped, not moved to unsuitable."""
    jobs = [
        {"id": "1", "companyName": "X", "overall": 3},
        {"id": "2", "companyName": "X", "overall": 7},
        {"id": "3", "companyName": "Y", "overall": 6},
    ]
    result = company_dedup_node({"filtered_jobs": jobs})
    assert "unsuitable_jobs" not in result
    assert {j["id"] for j in result["filtered_jobs"]} == {"2", "3"}
