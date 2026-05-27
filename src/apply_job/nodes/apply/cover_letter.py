from apply_job.nodes.apply.state import ApplyState
from apply_job.tools.cover_letter import generate_cover_letter_pdf


def generate_cover_letter_node(state: ApplyState) -> dict:
    job = state["jobs"][state["current_job_index"]]
    print("  Generating cover letter...")
    path = generate_cover_letter_pdf(job, state.get("resume_text", ""))
    print(f"  Cover letter: {path}")
    return {"cover_letter_path": path}
