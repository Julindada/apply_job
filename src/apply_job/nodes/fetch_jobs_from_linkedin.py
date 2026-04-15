"""
Node: fetch_jobs_from_linkedin

Wraps the fetch_jobs_from_linkedin tool as a LangGraph node.
Reads search_url / country from state, invokes the tool, writes raw_jobs back.
"""

from apply_job.state import AgentState
from apply_job.tools.fetch_jobs_from_linkedin import fetch_jobs_from_linkedin


def fetch_jobs_from_linkedin_node(state: AgentState) -> dict:
    """LangGraph node: invoke the fetch_jobs_from_linkedin tool and store results."""
    # search_url may be missing if resolve_url's state update wasn't persisted
    # (e.g. a retried run in LangGraph API). Fall back to recomputing it.
    search_url = state.get("search_url")
    if not search_url:
        from apply_job.nodes.resolve_search_url import resolve_search_url_node
        search_url = resolve_search_url_node(state)["search_url"]

    raw_jobs = fetch_jobs_from_linkedin.invoke({
        "search_url": search_url,
        "country": state["country"],
    })
    return {"raw_jobs": raw_jobs}
