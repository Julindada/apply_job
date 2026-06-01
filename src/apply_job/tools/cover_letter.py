"""
Tool: cover_letter

Generates a tailored cover letter PDF for a job using the LLM.
Called by the apply loop before the submit agent runs.
"""

import os
import tempfile
from pathlib import Path

from fpdf import FPDF
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from apply_job.config import settings

_COVER_LETTER_FILENAME = "cover_letter.pdf"

_PROMPT = """Write a professional cover letter for the following job application.

Job Title: {title}
Company: {company}
Job Description:
{description}

Candidate Resume:
{resume}

Instructions:
- Write 3-4 concise paragraphs
- Start directly with "Dear Hiring Manager,"
- Do not include date, address headers, or signature lines — body text only
- Tailor the content to the specific role and company
- Highlight the most relevant experience from the resume"""


def generate_cover_letter_pdf(job: dict, resume_text: str) -> str:
    """Generate a cover letter for the job and save it as a temp PDF.

    Returns the absolute path to the temp file. Caller is responsible for
    deleting it after use.
    """
    llm = ChatOpenAI(
        model=settings.apply_model,
        api_key=settings.apply_api_key,
        base_url=settings.apply_base_url,
        temperature=0.7,
    )

    prompt = _PROMPT.format(
        title=job.get("title", ""),
        company=job.get("companyName", ""),
        description=(job.get("descriptionText") or "")[:3000],
        resume=resume_text[:2000],
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    return _write_pdf(response.content.strip(), job.get("id", "job"))


def _write_pdf(text: str, job_id: str) -> str:
    # FPDF core fonts are Latin-1 only; replace unmappable chars rather than crash.
    safe = text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, safe)

    temp_dir = Path(tempfile.mkdtemp(prefix=f"cover_letter_{job_id}_"))
    path = temp_dir / _COVER_LETTER_FILENAME
    pdf.output(str(path))
    return os.path.abspath(path)
