"""
CLI entry point for apply-job.

Usage:
    apply-job run --country DE --resume data/resume.pdf
    apply-job run --country DE --resume data/resume.pdf --thread-id <id>  # resume
"""

import asyncio
import logging
import os
import uuid

import typer
from langgraph.types import Command

from apply_job.config import settings

app = typer.Typer(help="apply-job — LinkedIn job fetcher & filter")
_DEFAULT_APPLY_THREAD_ID = "apply-default"
_APPLY_LOG_FILENAME = "apply.log"


def _configure_apply_logging(log_path: str | None = None) -> str:
    resolved_log_path = log_path or os.path.join(settings.data_dir, _APPLY_LOG_FILENAME)
    os.makedirs(os.path.dirname(resolved_log_path), exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(resolved_log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[stream_handler, file_handler],
        force=True,
    )
    logging.getLogger(__name__).info("Apply log file: %s", resolved_log_path)
    return resolved_log_path


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
        result = graph.invoke(payload, config)
        interrupted = result.get("__interrupt__")
        if interrupted:
            payload = _handle_interrupt(interrupted)
        else:
            csv_paths = result.get("csv_paths") or []
            typer.echo(f"\nDone! CSV written to: {', '.join(csv_paths) or 'none'}")
            break


@app.command()
def apply(
    csv_path: str = typer.Option(None, "--csv", "-c", help="Path to suitable jobs CSV"),
    resume_path: str = typer.Option(None, "--resume", "-r", help="Path to resume PDF"),
    thread_id: str = typer.Option(
        None,
        "--thread-id",
        "-t",
        help="Resume a previous apply run by thread ID",
    ),
):
    """Open job application URLs one by one and let Agent complete each form."""
    _configure_apply_logging()
    resolved_csv = csv_path or os.path.join(settings.data_dir, "suitable.csv")
    resolved_resume = resume_path or settings.default_resume_path
    asyncio.run(_apply_loop(resolved_csv, resolved_resume, _resolve_apply_thread_id(thread_id)))


def _assert_chrome_reachable() -> None:
    import httpx

    from apply_job.nodes.apply._shared import resolve_cdp_url

    url = resolve_cdp_url(settings.cdp_url)
    try:
        httpx.get(f"{url}/json/version", timeout=3).raise_for_status()
    except Exception:
        typer.echo(
            f"\nError: cannot connect to Chrome at {settings.cdp_url}\n\n"
            "Start Chrome on your Mac with:\n\n"
            "  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome"
            " --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug"
            " --remote-allow-origins='*' --no-first-run\n",
            err=True,
        )
        raise SystemExit(1)


def _resolve_apply_thread_id(thread_id: str | None) -> str:
    return thread_id or _DEFAULT_APPLY_THREAD_ID


async def _apply_loop(csv_path: str, resume_path: str, thread_id: str) -> None:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from apply_job.apply_graph import build_apply_graph

    _assert_chrome_reachable()

    db_path = os.path.join(settings.data_dir, "apply_checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_apply_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        typer.echo(f"Using apply thread: {thread_id}")
        payload: dict | object = {"csv_path": csv_path, "resume_path": resume_path}

        while True:
            result = await graph.ainvoke(payload, config)
            interrupted = result.get("__interrupt__")
            if interrupted:
                payload = await _handle_apply_interrupt(interrupted)
            else:
                typer.echo("\nAll jobs processed.")
                return


async def _handle_apply_interrupt(interrupts: list) -> Command:
    decision = "continue"
    for iv in interrupts:
        v = iv.value
        idx = v.get("idx", 0)
        total = v.get("total", 0)
        typer.echo(f"\n{'─' * 60}")
        typer.echo(f"  [{idx + 1}/{total}] {v.get('title')} @ {v.get('company')}")
        typer.echo(f"  {v.get('link')}")
        if v.get("reason") == "submission_blocked":
            typer.echo("  Submission is still blocked after automated retries.")
            if v.get("message"):
                typer.echo(f"  Reason: {v.get('message')}")
            fields = v.get("fields") or []
            if fields:
                typer.echo("  Blocking fields:")
                for field in fields:
                    typer.echo(f"  - {field}")
        typer.echo(f"{'─' * 60}")
        if v.get("reason") == "submission_blocked":
            typer.echo("  Fix the blocking fields, submit the application, then press Enter.")
        else:
            typer.echo("  Fill in your basic info, then press Enter.")
        typer.echo("  Type  s + Enter  to skip this job.")
        # Run blocking stdin read in a thread so the event loop stays free
        # to complete any pending async generator cleanup.
        try:
            raw = await asyncio.to_thread(input, "  > ")
            decision = raw.strip().lower() or "continue"
        except EOFError:
            typer.echo("(EOF — skipping)")
            decision = "s"
    return Command(resume=decision)


def _handle_interrupt(interrupts: list) -> Command:
    """Print job info for each interrupted job and collect user decision."""
    decision = "u"
    for interrupt in interrupts:
        v = interrupt.value
        typer.echo("\n" + "─" * 56)
        typer.echo(f"  {v.get('title')} @ {v.get('companyName')}")
        typer.echo(f"  Overall : {v.get('overall')}/10")
        typer.echo(f"  Summary : {v.get('summary', '')}")
        typer.echo(f"  Link    : {v.get('link', '')}")
        decision = typer.prompt("\n  (s)uitable / (u)nsuitable", default="u")
    return Command(resume=decision)
