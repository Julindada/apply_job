"""
Node: init

First node in the pipeline. Runs before anything else to:
  1. Ensure data_dir exists
  2. Validate required environment variables
  3. Validate resume_path exists
  4. Archive suitable.csv → append to finished.csv, then clear suitable.csv
  5. Populate excluded_files in state: [finished.csv, unsuitable.csv]
"""

import os

from apply_job.config import settings
from apply_job.state import AgentState
from apply_job.tools.csv_ops import append_write_csv, overwriting_csv, read_csv

_SUITABLE_COLUMNS = [
    "id", "title", "companyName", "link", "descriptionText",
    "tech_stack", "experience_level", "language_requirements",
    "domain_fit", "overall", "classification", "summary",
]


def init_node(state: AgentState) -> dict:
    data_dir = settings.data_dir

    # 1. Ensure data_dir exists
    os.makedirs(data_dir, exist_ok=True)

    # 2. Validate required environment variables
    missing = [var for var in ("DASHSCOPE_V2_API_KEY", "APIFY_API_TOKEN")
               if not os.getenv(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )

    # 3. Validate resume_path exists; fall back to default if not provided
    resume_path = state.get("resume_path") or settings.default_resume_path
    if not os.path.exists(resume_path):
        raise FileNotFoundError(
            f"Resume file not found: '{resume_path}'. "
            f"Place your resume PDF at {settings.default_resume_path} "
            "or pass --resume <path>."
        )

    # 4. Archive suitable.csv → finished.csv, then clear suitable.csv
    suitable_path = os.path.join(data_dir, "suitable.csv")
    finished_path = os.path.join(data_dir, "finished.csv")

    suitable_rows = read_csv.invoke({"filepath": suitable_path})
    if suitable_rows:
        append_write_csv.invoke({
            "filepath": finished_path,
            "rows": suitable_rows,
            "fieldnames": _SUITABLE_COLUMNS,
        })
        overwriting_csv.invoke({
            "filepath": suitable_path,
            "rows": [],
            "fieldnames": _SUITABLE_COLUMNS,
        })

    # 5. Populate excluded_files so filter_jobs can deduplicate
    excluded_files = [finished_path, os.path.join(data_dir, "unsuitable.csv")]

    return {"resume_path": resume_path, "excluded_files": excluded_files}
