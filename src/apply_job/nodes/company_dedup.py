"""
Node: company_dedup

Third stage of the filtering pipeline — removes duplicate companies from
filtered_jobs by keeping only the job with the highest overall score.

Duplicates are silently dropped (NOT added to unsuitable_jobs).
"""

from apply_job.state import AgentState


def company_dedup_node(state: AgentState) -> dict:
    """LangGraph node: deduplicate jobs by companyName, keeping highest score."""

    jobs = state.get("filtered_jobs", [])
    best: dict[str, dict] = {}
    for job in jobs:
        company = job.get("companyName", "")
        if company not in best or job.get("overall", 0) > best[company].get("overall", 0):
            best[company] = job

    return {"filtered_jobs": list(best.values())}
