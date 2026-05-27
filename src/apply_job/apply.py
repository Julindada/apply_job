"""
Apply loop

Opens each job URL in the user's running Chrome (via CDP), waits for
the user to fill basic fields, then lets the LLM agent complete any
remaining required fields, upload the cover letter, and submit.

Usage (from inside the container):
    apply-job apply
    apply-job apply --csv /app/data/suitable.csv --resume /app/data/resume.pdf

Chrome must be started on the host with:
    /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
        --remote-debugging-port=9222 --no-first-run
"""

import asyncio
import os

from langchain_openai import ChatOpenAI
from pypdf import PdfReader

from apply_job.config import settings
from apply_job.tools.cover_letter import generate_cover_letter_pdf
from apply_job.tools.csv_ops import read_csv


async def run_apply_loop(csv_path: str, resume_path: str) -> None:
    from browser_use import Agent, Browser, BrowserConfig

    jobs = _load_jobs(csv_path)
    if not jobs:
        print(f"No jobs with links found in {csv_path}")
        return

    resume_text = _read_resume(resume_path)
    llm = ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.llm_base_url,
        temperature=0,
    )

    browser = Browser(config=BrowserConfig(cdp_url=settings.cdp_url))
    context = await browser.new_context()

    print(f"\nLoaded {len(jobs)} jobs from {csv_path}")
    print(f"Connecting to Chrome at {settings.cdp_url}\n")

    try:
        for i, job in enumerate(jobs):
            next_link = jobs[i + 1].get("link") if i + 1 < len(jobs) else None

            # Step 1: open job URL in a new tab
            nav_agent = Agent(
                task=(
                    f"Open a new browser tab and navigate to this URL, then stop immediately "
                    f"without doing anything else: {job['link']}"
                ),
                llm=llm,
                browser_context=context,
            )
            await nav_agent.run()

            # Step 2: wait for user to fill the form
            print(f"\n{'─' * 60}")
            print(f"  [{i + 1}/{len(jobs)}] {job.get('title')} @ {job.get('companyName')}")
            print(f"  {job.get('link')}")
            print(f"{'─' * 60}")
            print("  Fill in the form, then press Enter and the Agent will complete it.")
            print("  Type  s + Enter  to skip this job.\n")
            user_input = input("  > ").strip().lower()

            if user_input == "s":
                print("  Skipped.\n")
                continue

            # Step 3: generate tailored cover letter
            print("  Generating cover letter...")
            cover_letter_path = generate_cover_letter_pdf(job, resume_text)
            print(f"  Cover letter: {cover_letter_path}")

            # Step 4: agent fills remaining required fields, uploads cover letter, submits
            submit_agent = Agent(
                task=_build_submit_task(job, resume_text, cover_letter_path, next_link),
                llm=llm,
                browser_context=context,
            )
            await submit_agent.run()

            try:
                os.unlink(cover_letter_path)
            except OSError:
                pass

    finally:
        await context.close()
        await browser.close()

    print("\nAll jobs processed.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
   - Text or textarea question (e.g. "Why do you want to work here?",
     "Describe a challenge you overcame") →
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
