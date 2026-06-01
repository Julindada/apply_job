import logging
import os
import json
import re
from typing import Any

from langgraph.types import interrupt

from apply_job.nodes.apply._shared import browser_session, make_agent_kwargs
from apply_job.nodes.apply.state import ApplyState

_MAX_VALIDATION_RECOVERY_ATTEMPTS = 2


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
        await Agent(task=task, browser_session=session, **make_agent_kwargs()).run()
        status = await _check_submission_status(Agent, session)
        for attempt in range(_MAX_VALIDATION_RECOVERY_ATTEMPTS):
            if not status["blocked"]:
                break
            recovery_task = _build_validation_recovery_task(
                job=job,
                resume_text=resume_text,
                cover_letter_path=cover_letter_path,
                blocked_fields=status["fields"],
                next_link=next_link,
                attempt=attempt + 1,
            )
            await Agent(
                task=recovery_task,
                browser_session=session,
                **make_agent_kwargs(),
            ).run()
            status = await _check_submission_status(Agent, session)

    if status["blocked"]:
        decision = interrupt({
            "reason": "submission_blocked",
            "message": status["message"],
            "fields": status["fields"],
            "title": job.get("title"),
            "company": job.get("companyName"),
            "link": job.get("link"),
            "idx": idx,
            "total": len(jobs),
        })
        if str(decision).strip().lower() == "s":
            logging.warning("User skipped blocked application: %s", job.get("link"))

    if cover_letter_path:
        try:
            os.unlink(cover_letter_path)
        except OSError:
            logging.warning("Could not delete temp cover letter: %s", cover_letter_path)

    return {"cover_letter_path": None}


async def _check_submission_status(agent_cls: type, session: Any) -> dict:
    result = await agent_cls(
        task=_SUBMISSION_STATUS_TASK,
        browser_session=session,
        **make_agent_kwargs(),
    ).run()
    return _parse_submission_status(result.final_result() or "")


_SUBMISSION_STATUS_TASK = """Inspect the current browser page after a job application submit attempt.

Return ONLY a JSON object:
{
  "blocked": true if visible validation errors or empty required fields are still blocking submission, else false,
  "fields": list of visible field labels or validation messages still requiring action,
  "message": short human-readable summary
}

If the application appears submitted, completed, or the browser is already on the next job/new page, return:
{"blocked": false, "fields": [], "message": "submitted"}
"""


def _parse_submission_status(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logging.warning("submission status: could not parse output: %.200s", raw)
        return {"blocked": False, "fields": [], "message": "status parse failed"}
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        logging.warning("submission status: invalid JSON: %.200s", raw)
        return {"blocked": False, "fields": [], "message": "status parse failed"}

    fields = data.get("fields", [])
    if not isinstance(fields, list):
        fields = []
    return {
        "blocked": bool(data.get("blocked", False)),
        "fields": [str(field) for field in fields],
        "message": str(data.get("message", "")),
    }


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

If submission is blocked by validation errors, do not loop forever. Stop after one careful submit attempt.

--- Job context ---
Title: {job.get('title', '')}
Company: {job.get('companyName', '')}
Description:
{(job.get('descriptionText') or '')[:2000]}

--- Candidate context (from resume) ---
{resume_text[:1500]}"""


def _build_validation_recovery_task(
    job: dict,
    resume_text: str,
    cover_letter_path: str | None,
    blocked_fields: list[str],
    next_link: str | None,
    attempt: int,
) -> str:
    fields_hint = (
        "\n".join(f"  - {field}" for field in blocked_fields)
        if blocked_fields
        else "  - Scan the page for visible validation errors and empty required fields."
    )
    cl_line = (
        f"Cover letter file if needed: {cover_letter_path}"
        if cover_letter_path
        else "No cover letter file is available."
    )
    next_step = (
        f"If submission succeeds, open a new browser tab and navigate to: {next_link}"
        if next_link
        else "If submission succeeds, stop; this is the last job."
    )
    return f"""A previous job application submit attempt is still blocked by validation errors.

Recovery attempt: {attempt}/{_MAX_VALIDATION_RECOVERY_ATTEMPTS}

Fix these visible blocking fields or validation messages:
{fields_hint}

Use the job and resume context to answer text questions concisely.
Select reasonable dropdown/radio/checkbox options when required.
Do not change fields the user already completed unless the page explicitly marks them invalid.
{cl_line}

Click the submit/apply button once after fixing the blocking fields.
{next_step}

If the page is still blocked after this attempt, stop and leave it for manual user input.

--- Job context ---
Title: {job.get('title', '')}
Company: {job.get('companyName', '')}
Description:
{(job.get('descriptionText') or '')[:2000]}

--- Candidate context (from resume) ---
{resume_text[:1500]}"""
