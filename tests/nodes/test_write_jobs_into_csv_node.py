"""
Unit tests for nodes/write_jobs_into_csv.py
"""

import csv
import os

from apply_job.nodes.write_jobs_into_csv import (
    _SUITABLE_COLUMNS,
    _UNSUITABLE_COLUMNS,
    write_jobs_into_csv_node,
)


def _suitable_job(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": "Backend Engineer",
        "companyName": "Acme",
        "link": f"https://linkedin.com/jobs/{job_id}",
        "descriptionText": "Java Spring Boot.",
        "tech_stack": 8,
        "experience_level": 7,
        "language_requirements": 9,
        "domain_fit": 8,
        "overall": 8,
        "classification": "suitable",
        "summary": "Java主语言，符合JVM要求。",
    }


def _unsuitable_job(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": "Frontend Developer",
        "companyName": "Acme",
        "link": f"https://linkedin.com/jobs/{job_id}",
        "descriptionText": "React, TypeScript.",
        "tech_stack": 2,
        "experience_level": 6,
        "language_requirements": 4,
        "domain_fit": 3,
        "overall": 3,
        "classification": "unsuitable",
        "summary": "前端岗位，不符合后端要求。",
    }


def _state(tmp_path, filtered_jobs=None, unsuitable_jobs=None):
    return {
        "data_dir": str(tmp_path),
        "filtered_jobs": filtered_jobs or [],
        "unsuitable_jobs": unsuitable_jobs or [],
    }


# ---------------------------------------------------------------------------
# suitable.csv
# ---------------------------------------------------------------------------


def test_suitable_jobs_written_to_suitable_csv(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, filtered_jobs=[_suitable_job("1")]))
    assert (tmp_path / "suitable.csv").exists()


def test_suitable_csv_header(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, filtered_jobs=[_suitable_job("1")]))
    with open(tmp_path / "suitable.csv", newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == _SUITABLE_COLUMNS


def test_suitable_csv_row_values(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, filtered_jobs=[_suitable_job("42")]))
    with open(tmp_path / "suitable.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["id"] == "42"
    assert rows[0]["classification"] == "suitable"


# ---------------------------------------------------------------------------
# unsuitable.csv
# ---------------------------------------------------------------------------


def test_unsuitable_jobs_written_to_unsuitable_csv(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, unsuitable_jobs=[_unsuitable_job("1")]))
    assert (tmp_path / "unsuitable.csv").exists()


def test_unsuitable_csv_header(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, unsuitable_jobs=[_unsuitable_job("1")]))
    with open(tmp_path / "unsuitable.csv", newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == _UNSUITABLE_COLUMNS


def test_unsuitable_csv_row_values(tmp_path):
    write_jobs_into_csv_node(_state(tmp_path, unsuitable_jobs=[_unsuitable_job("99")]))
    with open(tmp_path / "unsuitable.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["id"] == "99"
    assert rows[0]["classification"] == "unsuitable"


# ---------------------------------------------------------------------------
# General behaviour
# ---------------------------------------------------------------------------


def test_empty_state_returns_no_csv_paths(tmp_path):
    result = write_jobs_into_csv_node(_state(tmp_path))
    assert result == {"csv_paths": []}
    assert not (tmp_path / "suitable.csv").exists()
    assert not (tmp_path / "unsuitable.csv").exists()


def test_returns_paths_for_both_files(tmp_path):
    result = write_jobs_into_csv_node(_state(
        tmp_path,
        filtered_jobs=[_suitable_job("1")],
        unsuitable_jobs=[_unsuitable_job("2")],
    ))
    assert os.path.join(str(tmp_path), "suitable.csv") in result["csv_paths"]
    assert os.path.join(str(tmp_path), "unsuitable.csv") in result["csv_paths"]


def test_data_dir_is_created_if_missing(tmp_path):
    nested = tmp_path / "subdir" / "data"
    write_jobs_into_csv_node({
        "data_dir": str(nested),
        "filtered_jobs": [_suitable_job("1")],
        "unsuitable_jobs": [],
    })
    assert (nested / "suitable.csv").exists()
