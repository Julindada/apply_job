from langgraph.types import interrupt

from apply_job.nodes.apply.state import ApplyState


def wait_for_user_node(state: ApplyState) -> dict:
    """Pause graph execution until the user signals they have filled in basic info."""
    job = state["jobs"][state["current_job_index"]]
    decision = interrupt({
        "title": job.get("title"),
        "company": job.get("companyName"),
        "link": job.get("link"),
        "idx": state["current_job_index"],
        "total": len(state["jobs"]),
    })
    return {"user_decision": str(decision).strip().lower() if decision else "continue"}


def route_after_wait(state: ApplyState) -> str:
    return "advance" if state.get("user_decision") == "s" else "analyze_form"
