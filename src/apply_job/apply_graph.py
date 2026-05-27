"""
Apply graph: semi-automated job application pipeline

Single-node graph that opens each job from suitable.csv in Chrome,
waits for the user to fill basic fields, then lets the LLM agent
complete the form and submit.

Registered in langgraph.json as "apply".
"""

from langgraph.graph import StateGraph, START, END

from apply_job.nodes.apply_jobs import ApplyState, apply_jobs_node

_builder = StateGraph(ApplyState)
_builder.add_node("apply_jobs", apply_jobs_node)
_builder.add_edge(START, "apply_jobs")
_builder.add_edge("apply_jobs", END)

apply_graph = _builder.compile()
