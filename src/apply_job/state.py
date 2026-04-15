from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    """LangGraph state definition for the job-fetch pipeline."""

    # --- Input ---
    country: str             # ISO country code, e.g. "DE". Determines the LinkedIn search URL.
    search_url: str          # Populated by resolve_search_url_node; do not set manually.
    excluded_files: list[str]  # CSV files whose job IDs should be excluded
    resume_path: str         # Path to the resume PDF used for LLM scoring

    # --- Pipeline state ---
    raw_jobs: list[dict]        # Raw job dicts returned by Apify (JSON-serializable)
    filtered_jobs: list[dict]   # Jobs after all filtering (suitable / pending), not written to CSV
    unsuitable_jobs: list[dict] # Jobs classified as unsuitable, written to unsuitable.csv
    csv_paths: Annotated[list[str], operator.add]  # Paths of CSV files written this run
