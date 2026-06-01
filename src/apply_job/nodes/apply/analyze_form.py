import json
import logging
import re

from apply_job.nodes.apply._shared import browser_session, make_agent_kwargs
from apply_job.nodes.apply.state import ApplyState

_TASK = (
    "Look at the current browser tab — it shows a job application form.\n"
    "Analyze the form and output ONLY a JSON object with these two keys:\n"
    '  "needs_cover_letter": true if there is a file upload field for a cover letter '
    "or motivation letter, else false\n"
    '  "required_fields": list of required field labels that are still empty '
    "(ignore name / email / phone already filled by the user)\n"
    'Example: {"needs_cover_letter": true, "required_fields": ["LinkedIn URL", "Why do you want this role?"]}\n'
    "Output ONLY the JSON, nothing else."
)


async def analyze_form_node(state: ApplyState) -> dict:
    """Ask the LLM agent to inspect the current form and report what still needs filling."""
    from browser_use import Agent

    async with browser_session() as session:
        result = await Agent(
            task=_TASK,
            browser_session=session,
            **make_agent_kwargs(),
        ).run()
    return _parse_output(result.final_result() or "")


def route_after_analyze(state: ApplyState) -> str:
    return "generate_cover_letter" if state.get("needs_cover_letter") else "fill_and_submit"


def _parse_output(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "needs_cover_letter": bool(data.get("needs_cover_letter", True)),
                "required_fields": list(data.get("required_fields", [])),
            }
        except json.JSONDecodeError:
            pass
    logging.warning("analyze_form: could not parse output, defaulting to needs_cover_letter=True: %.200s", raw)
    return {"needs_cover_letter": True, "required_fields": []}
