"""
Main graph: job-fetch pipeline

Linear pipeline:
  init → resolve_search_url → fetch_jobs_from_linkedin → rule_filter
    → llm_score → company_dedup → review_pending_jobs (human-in-the-loop)
    → write_jobs_into_csv

Required state inputs:
  country      — ISO country code, e.g. "DE". Determines the LinkedIn search URL.
  resume_path  — path to the resume PDF for LLM scoring

Environment variables (see config.py):
  DATA_DIR     — directory for all input/output files (default: "data")
"""

import os
import sqlite3

from langgraph.graph import StateGraph, START, END

from apply_job.config import settings
from apply_job.nodes import (
    init_node,
    resolve_search_url_node,
    fetch_jobs_from_linkedin_node,
    rule_filter_node,
    llm_score_node,
    company_dedup_node,
    review_pending_jobs_node,
    write_jobs_into_csv_node,
)
from apply_job.state import AgentState

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

_builder = StateGraph(AgentState)

_builder.add_node("init",            init_node)
_builder.add_node("resolve_url",     resolve_search_url_node)
_builder.add_node("fetch_jobs",      fetch_jobs_from_linkedin_node)
_builder.add_node("rule_filter",     rule_filter_node)
_builder.add_node("llm_score",       llm_score_node)
_builder.add_node("company_dedup",   company_dedup_node)
_builder.add_node("review_pending",  review_pending_jobs_node)
_builder.add_node("write_csv",       write_jobs_into_csv_node)

_builder.add_edge(START,             "init")
_builder.add_edge("init",            "resolve_url")
_builder.add_edge("resolve_url",     "fetch_jobs")
_builder.add_edge("fetch_jobs",      "rule_filter")
_builder.add_edge("rule_filter",     "llm_score")
_builder.add_edge("llm_score",       "company_dedup")
_builder.add_edge("company_dedup",   "review_pending")
_builder.add_edge("review_pending",  "write_csv")
_builder.add_edge("write_csv",       END)

# ---------------------------------------------------------------------------
# Persistence: SQLite checkpointer (disabled for LangGraph API / Studio)
# ---------------------------------------------------------------------------

checkpointer = None
if os.getenv("LANGGRAPH_DEV") or os.getenv("LANGGRAPH_API_URL"):
    # LangGraph dev / API handles persistence automatically
    pass
else:
    _conn = sqlite3.connect(
        os.path.join(settings.data_dir, "checkpoints.db"),
        check_same_thread=False,
    )
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver(_conn)

graph = _builder.compile(checkpointer=checkpointer)
