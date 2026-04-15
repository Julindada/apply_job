"""
Tool: csv_ops

General-purpose CSV tools for reading and writing local files.
Consolidates all CSV I/O logic that was previously scattered across
nodes/write_jobs_into_csv.py and tools/filter_jobs.py.
"""

import csv
import os
from pathlib import Path

from langchain_core.tools import tool


@tool
def read_csv(filepath: str, max_rows: int = -1) -> list[dict]:
    """Read a CSV file and return its rows as a list of dicts.

    Args:
        filepath: Path to the CSV file.
        max_rows: Maximum number of data rows to read. -1 means no limit.
    """
    if not os.path.exists(filepath):
        return []
    rows: list[dict] = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows != -1 and i >= max_rows:
                break
            rows.append(dict(row))
    return rows


def _base_write_csv(filepath: str, rows: list[dict], fieldnames: list[str], mode: str) -> str:
    """Shared write implementation for overwriting_csv and append_write_csv.

    Overwrite mode always writes the header; append mode writes it only when
    the file is new or empty.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = (mode == "w") or (not path.exists() or path.stat().st_size == 0)
    with open(filepath, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writerow(fieldnames)
        for row in rows:
            writer.writerow([_escape(row.get(col)) for col in fieldnames])
    return os.path.abspath(filepath)


@tool
def overwriting_csv(filepath: str, rows: list[dict], fieldnames: list[str]) -> str:
    """Write rows to a CSV file, overwriting any existing content.

    Args:
        filepath: Destination file path (parent directories are created if needed).
        rows: Data rows as a list of dicts. Keys not in fieldnames are ignored.
        fieldnames: Column order for the header and row extraction.

    Returns:
        Absolute path of the written file.
    """
    return _base_write_csv(filepath, rows, fieldnames, "w")


@tool
def append_write_csv(filepath: str, rows: list[dict], fieldnames: list[str]) -> str:
    """Append rows to a CSV file, writing the header only when the file is new.

    Args:
        filepath: Destination file path (parent directories are created if needed).
        rows: Data rows as a list of dicts. Keys not in fieldnames are ignored.
        fieldnames: Column order for the header and row extraction.

    Returns:
        Absolute path of the written file.
    """
    return _base_write_csv(filepath, rows, fieldnames, "a")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _escape(value) -> str:
    """Normalise a field value — mirrors escapeCsv() in Kotlin FileService.

    Converts non-string values (e.g. integer scores) to str before escaping.
    """
    text = "" if value is None else str(value)
    return text.replace('"', '""').replace("\r", " ").replace("\n", " ")
