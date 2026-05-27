from langgraph.graph import END

from apply_job.nodes.apply.state import ApplyState


def advance_node(state: ApplyState) -> dict:
    """Increment job index and reset per-job state."""
    return {
        "current_job_index": state["current_job_index"] + 1,
        "user_decision": None,
        "needs_cover_letter": False,
        "required_fields": [],
        "cover_letter_path": None,
    }


def route_after_advance(state: ApplyState) -> str:
    return "open_job" if state["current_job_index"] < len(state.get("jobs", [])) else END
