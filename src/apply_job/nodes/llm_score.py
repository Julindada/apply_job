"""
Node: llm_score

Second stage of the filtering pipeline — LLM scoring and classification against
the user's resume. Jobs are classified as suitable, unsuitable, or pending.
"""

import json
import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pypdf import PdfReader

from apply_job.config import settings
from apply_job.prompts.evaluate import EVALUATE_JOBS_PROMPT
from apply_job.state import AgentState

# Maximum jobs sent to the LLM in a single call.
# Scoring all jobs together keeps the rating scale consistent across the batch.
#
# qwen3.6-plus limits: input 983 616 tokens, output 65 536 tokens.
# Per-JD cost: ~815 input tokens (3000-char desc + metadata) + ~130 output tokens (JSON + summary).
# Output is the real bottleneck: 65 536 ÷ 130 ≈ 504 max jobs from output alone.
# Apify fetches at most 300 jobs per run, so 300 is the practical ceiling and guarantees
# the entire filtered list is scored in a single LLM call.
_SCORE_BATCH_SIZE = 300

# Maximum characters of descriptionText forwarded to the LLM per job.
# Truncating avoids hitting token limits while preserving enough signal for classification.
_MAX_DESC_CHARS = 6000


def llm_score_node(state: AgentState) -> dict:
    """LangGraph node: LLM scoring and classification."""

    jobs = state.get("filtered_jobs", [])
    if not jobs:
        return {"filtered_jobs": [], "unsuitable_jobs": []}

    resume_path = state.get("resume_path", "")
    resume_text = _read_resume(resume_path)

    llm = ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        temperature=0,
    )

    # Collect all scored results across batches into a flat list.
    scored: list[dict] = []
    for i in range(0, len(jobs), _SCORE_BATCH_SIZE):
        batch = jobs[i : i + _SCORE_BATCH_SIZE]
        scored.extend(_score_batch(llm, resume_text, batch))

    # Index scores by job ID for O(1) lookup during the merge pass below.
    score_map = {r["id"]: r for r in scored}

    filtered_jobs = []
    unsuitable_jobs = []
    for job in jobs:
        score = score_map.get(job.get("id", ""))
        # Skip jobs the LLM failed to score (e.g. JSON parse error for that batch).
        if score is None:
            continue
        # score fields take precedence; they may override raw Apify values for
        # shared keys (e.g. "title") with the LLM-cleaned version.
        merged = {**job, **score}
        if score.get("classification") == "unsuitable":
            print(f"LLM unsuitable: {job.get('id')} — {score.get('summary', '')}")
            unsuitable_jobs.append(merged)
        else:
            filtered_jobs.append(merged)

    return {"filtered_jobs": filtered_jobs, "unsuitable_jobs": unsuitable_jobs}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_resume(resume_path: str) -> str:
    """Extract plain text from a PDF resume."""
    path = os.path.expanduser(resume_path)
    if not os.path.exists(path):
        return ""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _score_batch(llm: ChatOpenAI, resume_text: str, jobs: list[dict]) -> list[dict]:
    """Send one batch of jobs to the LLM for scoring; return parsed results."""
    jobs_text = _format_jobs(jobs)
    prompt = EVALUATE_JOBS_PROMPT.format(
        resume_text=resume_text,
        jobs_text=jobs_text,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return _parse_scores(response.content)


def _format_jobs(jobs: list[dict]) -> str:
    """Serialise job dicts into a readable block for the prompt."""
    lines = []
    for job in jobs:
        # Truncate description to keep each job's token footprint bounded.
        desc = (job.get("descriptionText") or "")[:_MAX_DESC_CHARS]
        lines.append(
            f"---JOB---\n"
            f"id: {job.get('id')}\n"
            f"title: {job.get('title')}\n"
            f"companyName: {job.get('companyName')}\n"
            f"link: {job.get('link')}\n"
            f"descriptionText: {desc}"
        )
    return "\n\n".join(lines)


def _parse_scores(content: str) -> list[dict]:
    """Extract the JSON array from the LLM response."""
    # Strip markdown code fences if the model wrapped the output.
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        print(f"Failed to parse LLM score response: {content[:200]}")
        return []
