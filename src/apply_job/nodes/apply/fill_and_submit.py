import logging
import os

from apply_job.nodes.apply._shared import browser_session, make_llm
from apply_job.nodes.apply.state import ApplyState


async def fill_and_submit_node(state: ApplyState) -> dict:
    """Fill remaining required fields, upload cover letter if any, submit, open next job."""
    from browser_use import Agent

    idx = state["current_job_index"]
    job = state["jobs"][idx]
    jobs = state["jobs"]
    next_link = jobs[idx + 1].get("link") if idx + 1 < len(jobs) else None
    cover_letter_path = state.get("cover_letter_path")
    required_fields = state.get("required_fields") or []
    resume_text = state.get("resume_text", "")

    task = _build_task(job, resume_text, cover_letter_path, required_fields, next_link)
    async with browser_session() as session:
        await Agent(task=task, llm=make_llm(), browser_session=session).run()

    if cover_letter_path:
        try:
            os.unlink(cover_letter_path)
        except OSError:
            logging.warning("Could not delete temp cover letter: %s", cover_letter_path)

    return {"cover_letter_path": None}


def _build_task(
    job: dict,
    resume_text: str,
    cover_letter_path: str | None,
    required_fields: list[str],
    next_link: str | None,
) -> str:
    cl_line = (
        f"  - File upload for cover letter / motivation letter → upload: {cover_letter_path}"
        if cover_letter_path
        else "  - (no cover letter file to upload)"
    )
    fields_hint = (
        "\n".join(f"  - {f}" for f in required_fields)
        if required_fields
        else "  - (scan the page yourself for any remaining required fields)"
    )
    next_step = (
        f"5. Open a new browser tab and navigate to: {next_link}"
        if next_link
        else "5. This was the last job — no next URL to open."
    )
    return f"""You are helping complete a job application form.
The user has already filled in their basic personal information (name, email, phone, etc.).

Complete these steps in order:

1. Identify all remaining empty required fields on the page. Known required fields still to fill:
{fields_hint}

2. For each empty required field:
{cl_line}
   - Text / textarea question → write a concise, relevant answer using the job and resume context below
   - Dropdown / radio / checkbox → select the most appropriate option

3. Do NOT modify any field the user has already filled in.

4. Click the submit or apply button to submit the application.

{next_step}

--- Job context ---
Title: {job.get('title', '')}
Company: {job.get('companyName', '')}
Description:
{(job.get('descriptionText') or '')[:2000]}

--- Candidate context (from resume) ---
{resume_text[:1500]}"""
