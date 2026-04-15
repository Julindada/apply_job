"""
Node: review_pending_jobs

Human-in-the-loop node that sits between filter_jobs and write_csv.

For each job whose classification is "pending", execution is paused via
interrupt() and the job's key info is shown to the user. The user replies
with "s" (suitable) or "u" (unsuitable); the job is then moved to the
appropriate output list.

Jobs already classified as "suitable" pass through unchanged.
"""

from langgraph.types import interrupt

from apply_job.state import AgentState


def review_pending_jobs_node(state: AgentState) -> dict:
    suitable = [j for j in state["filtered_jobs"] if j.get("classification") != "pending"]
    pending  = [j for j in state["filtered_jobs"] if j.get("classification") == "pending"]

    if not pending:
        return {}

    newly_unsuitable: list[dict] = []

    for job in pending:
        # Pause and show the job summary to the user.
        decision: str = interrupt({
            "action": "classify_pending_job",
            "id":          job.get("id"),
            "title":       job.get("title"),
            "companyName": job.get("companyName"),
            "link":        job.get("link"),
            "overall":     job.get("overall"),
            "summary":     job.get("summary"),
            "prompt":      'Reply "s" for suitable or "u" for unsuitable.',
        })

        if _is_suitable(decision):
            suitable.append({**job, "classification": "suitable"})
        else:
            newly_unsuitable.append({**job, "classification": "unsuitable"})

    return {
        "filtered_jobs":  suitable,
        "unsuitable_jobs": state.get("unsuitable_jobs", []) + newly_unsuitable,
    }


def _is_suitable(answer: str) -> bool:
    """Accept 's' / 'suitable' / 'yes' / 'y' as suitable; anything else is unsuitable."""
    return answer.strip().lower() in {"s", "suitable", "yes", "y"}
