"""
Apply graph: semi-automated job application pipeline.

Node sequence:
  load_jobs → open_job → wait_for_user → analyze_form
    → (generate_cover_letter →) fill_and_submit → advance → (loop or END)

Registered in langgraph.json as "apply".
"""

from langgraph.graph import StateGraph, START, END

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


def build_apply_graph(checkpointer=None):
    """Compile the apply graph with an optional checkpointer."""
    builder = StateGraph(ApplyState)

    builder.add_node("load_jobs",             load_jobs_node)
    builder.add_node("open_job",              open_job_node)
    builder.add_node("wait_for_user",         wait_for_user_node)
    builder.add_node("analyze_form",          analyze_form_node)
    builder.add_node("generate_cover_letter", generate_cover_letter_node)
    builder.add_node("fill_and_submit",       fill_and_submit_node)
    builder.add_node("advance",               advance_node)

    builder.add_edge(START, "load_jobs")
    builder.add_conditional_edges("load_jobs",     route_after_load)
    builder.add_edge("open_job", "wait_for_user")
    builder.add_conditional_edges("wait_for_user", route_after_wait)
    builder.add_conditional_edges("analyze_form",  route_after_analyze)
    builder.add_edge("generate_cover_letter", "fill_and_submit")
    builder.add_edge("fill_and_submit",       "advance")
    builder.add_conditional_edges("advance",       route_after_advance)

    return builder.compile(checkpointer=checkpointer)


# No checkpointer here — LangGraph Studio manages its own persistence.
# The CLI creates an AsyncSqliteSaver at runtime before invoking the graph.
apply_graph = build_apply_graph()
