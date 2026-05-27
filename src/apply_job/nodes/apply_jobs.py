"""
Node: apply_jobs

Semi-automated job application loop. Opens each job URL in the user's
Chrome (via CDP), waits for the user to fill basic fields, then lets
the LLM agent complete remaining required fields, upload the cover
letter, and submit. Opens the next job in a new tab automatically.

Runs as a single async node inside apply_graph. Uses input() directly
so it works under `docker exec -it`.
"""

import os
from contextlib import asynccontextmanager
from typing import TypedDict

from langchain_openai import ChatOpenAI
from pypdf import PdfReader

from apply_job.config import settings
from apply_job.tools.cover_letter import generate_cover_letter_pdf
from apply_job.tools.csv_ops import read_csv


class ApplyState(TypedDict):
    csv_path: str
    resume_path: str


async def apply_jobs_node(state: ApplyState) -> dict:
    """LangGraph node: interactive apply loop driven by the user."""
    from browser_use import Agent

    jobs = _load_jobs(state["csv_path"])
    if not jobs:
        print(f"No jobs with links found in {state['csv_path']}")
        return {}

    resume_text = _read_resume(state["resume_path"])
    llm = _make_llm()

    print(f"\nLoaded {len(jobs)} jobs. Connecting to Chrome at {settings.cdp_url}")

    for i, job in enumerate(jobs):
        next_link = jobs[i + 1].get("link") if i + 1 < len(jobs) else None

        # Step 1: open job URL in a new tab
        async with _browser_session() as ctx:
            await Agent(
                task=(
                    f"Open a new browser tab, navigate to this URL, then stop immediately: "
                    f"{job['link']}"
                ),
                llm=llm,
                browser_context=ctx,
            ).run()

        # Step 2: wait for user to fill the form
        print(f"\n{'─' * 60}")
        print(f"  [{i + 1}/{len(jobs)}] {job.get('title')} @ {job.get('companyName')}")
        print(f"  {job.get('link')}")
        print(f"{'─' * 60}")
        print("  Fill in the form, then press Enter for Agent to complete it.")
        print("  Type  s + Enter  to skip this job.\n")
        user_input = input("  > ").strip().lower()

        if user_input == "s":
            print("  Skipped.\n")
            continue

        # Step 3: generate tailored cover letter
        print("  Generating cover letter...")
        cover_letter_path = generate_cover_letter_pdf(job, resume_text)
        print(f"  Cover letter: {cover_letter_path}")

        # Step 4: agent fills remaining required fields, uploads CL, submits
        async with _browser_session() as ctx:
            await Agent(
                task=_build_submit_task(job, resume_text, cover_letter_path, next_link),
                llm=llm,
                browser_context=ctx,
            ).run()

        try:
            os.unlink(cover_letter_path)
        except OSError:
            pass

    print("\nAll jobs processed.")
    return {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _browser_session():
    from browser_use import Browser, BrowserConfig

    browser = Browser(config=BrowserConfig(cdp_url=settings.cdp_url))
    ctx = await browser.new_context()
    try:
        yield ctx
    finally:
        await ctx.close()
        await browser.close()


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.llm_base_url,
        temperature=0,
    )


def _build_submit_task(
    job: dict,
    resume_text: str,
    cover_letter_path: str,
    next_link: str | None,
) -> str:
    next_step = (
        f"5. Open a new tab and navigate to: {next_link}"
        if next_link
        else "5. This was the last job — no next URL to open."
    )

    return f"""You are helping complete a job application form.
The user has already filled in their basic personal information (name, email, phone, etc.).

Complete these steps in order:

1. Scan the current page for every required field (marked with * or the HTML 'required'
   attribute) that is still empty. For each empty required field:
   - File upload for a cover letter or motivation letter →
     upload the file at: {cover_letter_path}
   - Text or textarea question (e.g. "Why do you want to work here?") →
     write a concise, relevant answer using the job and resume context below
   - Dropdown, radio button, or checkbox →
     select the most appropriate option

2. Do NOT modify any field the user has already filled in.

3. If required fields remain empty after your best effort, print a warning
   listing them but continue to the next step.

4. Click the submit or apply button to submit the application.

{next_step}

--- Job context ---
Title: {job.get('title', '')}
Company: {job.get('companyName', '')}
Description:
{(job.get('descriptionText') or '')[:2000]}

--- Candidate context (from resume) ---
{resume_text[:1500]}"""


def _load_jobs(csv_path: str) -> list[dict]:
    rows = read_csv.invoke({"filepath": csv_path, "max_rows": 500})
    return [r for r in rows if r.get("link")]


def _read_resume(resume_path: str) -> str:
    path = os.path.expanduser(resume_path)
    if not os.path.exists(path):
        return ""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
