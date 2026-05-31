"""
Node: write_jobs_into_csv

Persists two CSV files inside data_dir at the end of each pipeline run:
  - suitable.csv   — filtered_jobs (suitable + pending confirmed by user)
  - unsuitable.csv — jobs the LLM or user classified as unsuitable

Both files are read back as excluded_files at the start of the next run.
"""

import os

from apply_job.config import settings
from apply_job.nodes.apply.progress import reset_progress
from apply_job.state import AgentState
from apply_job.tools.csv_ops import overwriting_csv, append_write_csv

_SUITABLE_COLUMNS = [
    "id", "title", "companyName", "link", "descriptionText",
    "tech_stack", "experience_level", "language_requirements",
    "domain_fit", "overall", "classification", "summary",
]

_UNSUITABLE_COLUMNS = [
    "id", "title", "companyName", "link", "descriptionText",
    "tech_stack", "experience_level", "language_requirements",
    "domain_fit", "overall", "classification", "summary",
]


def write_jobs_into_csv_node(state: AgentState) -> dict:
    data_dir = settings.data_dir
    suitable_jobs: list[dict] = state.get("filtered_jobs", [])
    unsuitable_jobs: list[dict] = state.get("unsuitable_jobs", [])

    csv_paths: list[str] = []

    if suitable_jobs:
        path = os.path.join(data_dir, "suitable.csv")
        reset_progress(path)
        overwriting_csv.invoke({
            "filepath": path,
            "rows": suitable_jobs,
            "fieldnames": _SUITABLE_COLUMNS,
        })
        csv_paths.append(path)

    if unsuitable_jobs:
        path = os.path.join(data_dir, "unsuitable.csv")
        append_write_csv.invoke({
            "filepath": path,
            "rows": unsuitable_jobs,
            "fieldnames": _UNSUITABLE_COLUMNS,
        })
        csv_paths.append(path)

    return {"csv_paths": csv_paths}
