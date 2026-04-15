"""
Main graph: job-fetch pipeline

Linear pipeline:
  resolve_search_url → fetch_jobs_from_linkedin → filter_jobs
    → review_pending_jobs (human-in-the-loop) → write_jobs_into_csv

Required state inputs:
  country      — ISO country code, e.g. "DE". Determines the LinkedIn search URL.
  resume_path  — path to the resume PDF for LLM scoring

Optional state inputs:
  excluded_files — override the default [DATA_DIR/suitable.csv, DATA_DIR/unsuitable.csv]

Environment variables (see config.py):
  DATA_DIR     — directory for all input/output files (default: "data")
"""

import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

from apply_job.config import settings
from apply_job.nodes import (
    resolve_search_url_node,
    fetch_jobs_from_linkedin_node,
    filter_jobs_node,
    review_pending_jobs_node,
    write_jobs_into_csv_node,
)
from apply_job.state import AgentState

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

_builder = StateGraph(AgentState)

_builder.add_node("resolve_url",     resolve_search_url_node)
_builder.add_node("fetch_jobs",      fetch_jobs_from_linkedin_node)
_builder.add_node("filter_jobs",     filter_jobs_node)
_builder.add_node("review_pending",  review_pending_jobs_node)
_builder.add_node("write_csv",       write_jobs_into_csv_node)

_builder.add_edge(START,             "resolve_url")
_builder.add_edge("resolve_url",     "fetch_jobs")
_builder.add_edge("fetch_jobs",      "filter_jobs")
_builder.add_edge("filter_jobs",     "review_pending")
_builder.add_edge("review_pending",  "write_csv")
_builder.add_edge("write_csv",       END)

# ---------------------------------------------------------------------------
# Persistence: SQLite checkpointer
# ---------------------------------------------------------------------------

os.makedirs(settings.data_dir, exist_ok=True)
_conn = sqlite3.connect(
    os.path.join(settings.data_dir, "checkpoints.db"),
    check_same_thread=False,
)
graph = _builder.compile(checkpointer=SqliteSaver(_conn))
