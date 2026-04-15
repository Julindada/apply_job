"""
CLI entry point for apply-job.

Usage:
    apply-job run --country DE --resume data/resume.pdf
    apply-job run --country DE --resume data/resume.pdf --thread-id <id>  # resume
"""

import uuid

import typer
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

app = typer.Typer(help="apply-job — LinkedIn job fetcher & filter")


@app.command()
def run(
    country: str = typer.Option(..., "--country", "-c", help="ISO country code, e.g. DE, NL, GB"),
    resume_path: str = typer.Option(..., "--resume", "-r", help="Path to resume PDF"),
    thread_id: str = typer.Option(None, "--thread-id", "-t", help="Resume a previous run by thread ID"),
):
    """Fetch, filter and review LinkedIn jobs."""
    # Import here to avoid loading the graph (and opening the DB) at import time.
    from apply_job.graph import graph

    if thread_id is None:
        thread_id = str(uuid.uuid4())
        typer.echo(f"Starting new run  (thread: {thread_id})")
    else:
        typer.echo(f"Resuming run (thread: {thread_id})")

    config = {"configurable": {"thread_id": thread_id}}
    payload = {"country": country, "resume_path": resume_path}

    while True:
        try:
            result = graph.invoke(payload, config)
            csv_paths = result.get("csv_paths") or []
            typer.echo(f"\nDone! CSV written to: {', '.join(csv_paths) or 'none'}")
            break
        except GraphInterrupt as exc:
            payload = _handle_interrupt(exc)


def _handle_interrupt(exc: GraphInterrupt) -> Command:
    """Print job info for each interrupted job and collect user decision."""
    decision = "u"
    for interrupt in exc.interrupts:
        v = interrupt.value
        typer.echo("\n" + "─" * 56)
        typer.echo(f"  {v.get('title')} @ {v.get('companyName')}")
        typer.echo(f"  Overall : {v.get('overall')}/10")
        typer.echo(f"  Summary : {v.get('summary', '')}")
        typer.echo(f"  Link    : {v.get('link', '')}")
        decision = typer.prompt("\n  (s)uitable / (u)nsuitable", default="u")
    return Command(resume=decision)
