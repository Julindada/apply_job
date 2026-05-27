"""
Unit tests for company rejection matching in tools/filter_jobs.py.
"""

import tempfile
import os

from apply_job.tools.filter_jobs import (
    _normalize_company,
    _is_rejected_company,
    _load_rejected_companies,
    _should_keep,
)


# ---------------------------------------------------------------------------
# _normalize_company
# ---------------------------------------------------------------------------

def test_normalize_lowercase():
    assert _normalize_company("Google") == "google"


def test_normalize_strips_legal_suffix():
    assert _normalize_company("Ubiquiti Inc.") == "ubiquiti"


def test_normalize_strips_gmbh():
    assert _normalize_company("Siemens GmbH") == "siemens"


def test_normalize_removes_punctuation():
    assert _normalize_company("JD.com") == "jd com"


def test_normalize_removes_parens():
    assert _normalize_company("Atolls (Global Savings Group)") == "atolls global savings group"


# ---------------------------------------------------------------------------
# _is_rejected_company
# ---------------------------------------------------------------------------

def test_exact_match():
    assert _is_rejected_company("Google", {"Google"})


def test_case_insensitive():
    assert _is_rejected_company("flaconi", {"Flaconi"})


def test_file_has_suffix_job_does_not():
    # File: "Ubiquiti Inc."  LinkedIn: "Ubiquiti"
    assert _is_rejected_company("Ubiquiti", {"Ubiquiti Inc."})


def test_job_has_suffix_file_does_not():
    # File: "Redcare Pharmacy"  LinkedIn: "Redcare Pharmacy N.V."
    assert _is_rejected_company("Redcare Pharmacy N.V.", {"Redcare Pharmacy"})


def test_file_has_parent_company():
    # File: "Atolls (Global Savings Group)"  LinkedIn: "Global Savings Group"
    assert _is_rejected_company("Global Savings Group", {"Atolls (Global Savings Group)"})


def test_no_match():
    assert not _is_rejected_company("Shopify", {"Google", "Meta", "Amazon"})


def test_empty_company_name():
    assert not _is_rejected_company("", {"Google"})


def test_empty_rejected_set():
    assert not _is_rejected_company("Google", set())


# ---------------------------------------------------------------------------
# _load_rejected_companies
# ---------------------------------------------------------------------------

def test_load_parses_date_prefix():
    content = "2026-01-06  Delivery Hero\n2026-03-23  Canva\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = _load_rejected_companies(path)
        assert result == {"Delivery Hero", "Canva"}
    finally:
        os.unlink(path)


def test_load_skips_comments():
    content = "# this is a comment\n2026-01-06  Delivery Hero\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        assert _load_rejected_companies(path) == {"Delivery Hero"}
    finally:
        os.unlink(path)


def test_load_missing_file_returns_empty():
    assert _load_rejected_companies("/nonexistent/path.txt") == set()


# ---------------------------------------------------------------------------
# _should_keep — company rejection integration
# ---------------------------------------------------------------------------

def _make_job(company: str) -> dict:
    return {
        "id": "42",
        "title": "Backend Engineer",
        "companyName": company,
        "descriptionText": "Java Spring Boot microservices.",
    }


def test_should_keep_rejects_matching_company():
    job = _make_job("Flaconi")
    assert not _should_keep(job, set(), {"flaconi"})


def test_should_keep_passes_non_rejected_company():
    job = _make_job("Shopify")
    assert _should_keep(job, set(), {"Google", "Meta"})


def test_should_keep_no_rejected_set():
    job = _make_job("Google")
    assert _should_keep(job, set(), None)
