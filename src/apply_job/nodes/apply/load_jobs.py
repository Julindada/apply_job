import logging
import os

from langgraph.graph import END
from pypdf import PdfReader

from apply_job.config import settings
from apply_job.nodes.apply.state import ApplyState
from apply_job.tools.csv_ops import read_csv


def load_jobs_node(state: ApplyState) -> dict:
    jobs = _load_jobs(state["csv_path"])
    resume_text = _read_resume(state["resume_path"])
    if not jobs:
        logging.warning("No jobs with links found in %s", state["csv_path"])
    else:
        print(f"\nLoaded {len(jobs)} jobs. Chrome should be running at {settings.cdp_url}")
    return {
        "jobs": jobs,
        "resume_text": resume_text,
        "current_job_index": 0,
        "user_decision": None,
        "needs_cover_letter": False,
        "required_fields": [],
        "cover_letter_path": None,
    }


def route_after_load(state: ApplyState) -> str:
    return "open_job" if state.get("jobs") else END


def _load_jobs(csv_path: str) -> list[dict]:
    rows = read_csv.invoke({"filepath": csv_path, "max_rows": 500})
    return [r for r in rows if r.get("link")]


def _read_resume(resume_path: str) -> str:
    path = os.path.expanduser(resume_path)
    if not os.path.exists(path):
        logging.warning("Resume not found: %s", path)
        return ""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
