import hashlib
import json
import logging
import os
from typing import Any

_PROGRESS_FILENAME = "apply_progress.json"


def progress_path(csv_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(csv_path)), _PROGRESS_FILENAME)


def load_next_job_index(csv_path: str, total_jobs: int) -> int:
    path = progress_path(csv_path)
    progress = _read_progress(path)
    if not progress:
        return 0

    expected_hash = _csv_hash(csv_path)
    if progress.get("csv_path") != os.path.abspath(csv_path):
        return 0
    if progress.get("csv_hash") != expected_hash:
        return 0

    raw_index = progress.get("next_job_index", 0)
    if not isinstance(raw_index, int):
        return 0
    return max(0, min(raw_index, total_jobs))


def save_next_job_index(csv_path: str, next_job_index: int) -> None:
    path = progress_path(csv_path)
    payload = {
        "csv_path": os.path.abspath(csv_path),
        "csv_hash": _csv_hash(csv_path),
        "next_job_index": max(0, next_job_index),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def reset_progress(csv_path: str) -> None:
    path = progress_path(csv_path)
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    except OSError:
        logging.warning("Could not reset apply progress: %s", path)


def _read_progress(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        logging.warning("Could not read apply progress: %s", path)
        return {}
    return data if isinstance(data, dict) else {}


def _csv_hash(csv_path: str) -> str:
    digest = hashlib.sha256()
    try:
        with open(csv_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return ""
    return digest.hexdigest()
