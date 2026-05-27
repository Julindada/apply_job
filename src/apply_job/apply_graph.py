"""
Apply graph: semi-automated job application pipeline.

Node sequence:
  load_jobs → open_job → wait_for_user → analyze_form
    → (generate_cover_letter →) fill_and_submit → advance → (loop or END)

Registered in langgraph.json as "apply".
"""

import os
import sqlite3
import tempfile

from langgraph.graph import StateGraph, START, END

from apply_job.config import settings
from apply_job.nodes.apply import (
    ApplyState,
    load_jobs_node,
    open_job_node,
    wait_for_user_node,
    analyze_form_node,
    generate_cover_letter_node,
    fill_and_submit_node,
    advance_node,
    route_after_load,
    route_after_wait,
    route_after_analyze,
    route_after_advance,
)

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

_builder = StateGraph(ApplyState)

_builder.add_node("load_jobs",             load_jobs_node)
_builder.add_node("open_job",              open_job_node)
_builder.add_node("wait_for_user",         wait_for_user_node)
_builder.add_node("analyze_form",          analyze_form_node)
_builder.add_node("generate_cover_letter", generate_cover_letter_node)
_builder.add_node("fill_and_submit",       fill_and_submit_node)
_builder.add_node("advance",               advance_node)

_builder.add_edge(START, "load_jobs")
_builder.add_conditional_edges("load_jobs",     route_after_load)
_builder.add_edge("open_job", "wait_for_user")
_builder.add_conditional_edges("wait_for_user", route_after_wait)
_builder.add_conditional_edges("analyze_form",  route_after_analyze)
_builder.add_edge("generate_cover_letter", "fill_and_submit")
_builder.add_edge("fill_and_submit",       "advance")
_builder.add_conditional_edges("advance",       route_after_advance)

# ---------------------------------------------------------------------------
# Persistence: SQLite checkpointer (required for interrupt/resume)
# ---------------------------------------------------------------------------

checkpointer = None
if os.getenv("LANGGRAPH_DEV") or os.getenv("LANGGRAPH_API_URL"):
    pass
else:
    try:
        os.makedirs(settings.data_dir, exist_ok=True)
        _db_dir = settings.data_dir
    except OSError:
        _db_dir = tempfile.gettempdir()
    _conn = sqlite3.connect(
        os.path.join(_db_dir, "apply_checkpoints.db"),
        check_same_thread=False,
    )
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver(_conn)

apply_graph = _builder.compile(checkpointer=checkpointer)
