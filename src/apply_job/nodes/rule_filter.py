"""
Node: rule_filter

First stage of the filtering pipeline — dedup, language detection, and keyword
exclusion. Fast, no LLM call.
"""

import os

from apply_job.config import settings
from apply_job.state import AgentState
from apply_job.tools.filter_jobs import _load_excluded_ids, _load_rejected_companies, _should_keep


def rule_filter_node(state: AgentState) -> dict:
    """LangGraph node: rule-based pre-filter before LLM scoring."""

    default_excluded = [
        os.path.join(settings.data_dir, "finished_jobs.csv"),
        os.path.join(settings.data_dir, "unsuitable.csv"),
    ]
    excluded_ids = _load_excluded_ids(state.get("excluded_files") or default_excluded)
    rejected_companies = _load_rejected_companies(
        os.path.join(settings.data_dir, "rejection_companies_sorted.txt")
    )
    passed = [
        job for job in state.get("raw_jobs", [])
        if _should_keep(job, excluded_ids, rejected_companies)
    ]
    return {"filtered_jobs": passed}
