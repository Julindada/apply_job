"""
Node: fetch_jobs_from_linkedin

Wraps the fetch_jobs_from_linkedin tool as a LangGraph node.
Reads search_url / country from state, invokes the tool, writes raw_jobs back.
"""

from apply_job.state import AgentState
from apply_job.tools.fetch_jobs_from_linkedin import fetch_jobs_from_linkedin


def fetch_jobs_from_linkedin_node(state: AgentState) -> dict:
    """LangGraph node: invoke the fetch_jobs_from_linkedin tool and store results."""
    raw_jobs = fetch_jobs_from_linkedin.invoke({
        "search_url": state["search_url"],
        "country": state["country"],
    })
    return {"raw_jobs": raw_jobs}
