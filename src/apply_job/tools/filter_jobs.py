"""
Tool: filter_jobs

Filters raw Apify job dicts by:
  1. Dedup — drops jobs whose ID already appears in finished_jobs.csv or unsuitable_jobs.csv
  2. Language detection — drops non-English postings (de / nl / es / pl)
  3. Keyword exclusion — drops obvious non-backend roles (frontend, fullstack, etc.)

Mirrors LinkedInWebService.shouldKeepBackendJob() + the filtering loop inside
getJobDescFromLinkedIn() from the Kotlin implementation.
"""

import re

from langchain_core.tools import tool

from apply_job.tools.csv_ops import read_csv

_EXCLUDED_LANGUAGES = {"de", "nl", "es", "pl"}

_LEGAL_SUFFIXES = re.compile(
    r"\b(inc|llc|gmbh|ltd|corp|co|ag|se|bv|nv|plc|pty|srl|sas|sarl)\b"
)

_EXCLUDED_KEYWORDS = {
    "frontend",
    "front end",
    "front-end",
    "fullstack",
    "full stack",
    "full-stack",
}

# langdetect is unreliable on very short strings; skip detection below this length.
_MIN_DETECT_LEN = 50


@tool
def filter_jobs(
    raw_jobs: list[dict],
    excluded_files: list[str] | None = None,
) -> list[dict]:
    """Filter raw LinkedIn job dicts and return only suitable backend jobs.

    Args:
        raw_jobs: Raw job dicts returned by fetch_jobs_from_linkedin.
        excluded_files: CSV files whose first column contains job IDs to skip.
                        Pass an empty list or None to skip the dedup check.
    """
    excluded_ids = _load_excluded_ids(excluded_files or [])
    return [job for job in raw_jobs if _should_keep(job, excluded_ids)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_excluded_ids(filepaths: list[str], max_rows: int = 1000) -> set[str]:
    """Read job IDs (first column) from one or more CSV files via read_csv tool."""
    ids: set[str] = set()
    for path in filepaths:
        rows = read_csv.invoke({"filepath": path, "max_rows": max_rows})
        for row in rows:
            if row:
                first_col = next(iter(row.values()), None)
                if first_col:
                    ids.add(first_col)
    return ids


def _should_keep(
    job: dict,
    excluded_ids: set[str],
    rejected_companies: set[str] | None = None,
) -> bool:
    job_id = job.get("id", "")
    if job_id in excluded_ids:
        print(f"excluded job: {job_id}")
        return False

    if rejected_companies:
        company = job.get("companyName") or ""
        if _is_rejected_company(company, rejected_companies):
            print(f"rejected company: {company}")
            return False

    title = job.get("title") or ""
    description = job.get("descriptionText") or ""

    for text in (title, description):
        if _is_excluded_language(text):
            return False

    normalized = _normalize(f"{title} {description}")
    return not any(kw in normalized for kw in _EXCLUDED_KEYWORDS)


def _load_rejected_companies(filepath: str) -> set[str]:
    """Parse rejection_companies_sorted.txt — format: 'YYYY-MM-DD  Company Name'."""
    companies: set[str] = set()
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                companies.add(parts[1].strip() if len(parts) >= 2 else parts[0])
    except FileNotFoundError:
        pass
    return companies


def _normalize_company(name: str) -> str:
    name = name.lower()
    name = _LEGAL_SUFFIXES.sub("", name)
    name = re.sub(r"[^\w\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _is_rejected_company(company: str, rejected: set[str]) -> bool:
    normalized_job = _normalize_company(company)
    if not normalized_job:
        return False
    for r in rejected:
        normalized_r = _normalize_company(r)
        if normalized_r and (normalized_r in normalized_job or normalized_job in normalized_r):
            return True
    return False


def _is_excluded_language(text: str) -> bool:
    if len(text.strip()) < _MIN_DETECT_LEN:
        return False
    try:
        from langdetect import detect  # type: ignore
        return detect(text) in _EXCLUDED_LANGUAGES
    except Exception:
        return False


def _normalize(text: str) -> str:
    text = text.lower().replace("-", " ").replace("/", " ")
    return re.sub(r"\s+", " ", text).strip()
