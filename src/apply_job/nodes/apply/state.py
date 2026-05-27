from typing import TypedDict


class ApplyState(TypedDict):
    # Inputs
    csv_path: str
    resume_path: str
    # Loaded by load_jobs
    jobs: list[dict]
    resume_text: str
    current_job_index: int
    # Per-job ephemeral state (reset by advance)
    user_decision: str | None
    needs_cover_letter: bool
    required_fields: list[str]
    cover_letter_path: str | None
