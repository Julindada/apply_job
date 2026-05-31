import csv
import json

from apply_job.nodes.apply.advance import advance_node
from apply_job.nodes.apply.progress import (
    load_next_job_index,
    progress_path,
    save_next_job_index,
)


def _write_csv(path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "link"])
        writer.writeheader()
        writer.writerows(rows)


def test_load_next_job_index_resumes_when_csv_matches(tmp_path):
    csv_path = tmp_path / "suitable.csv"
    _write_csv(csv_path, [{"id": "1", "link": "https://example.com/1"}])
    save_next_job_index(str(csv_path), 1)

    assert load_next_job_index(str(csv_path), total_jobs=3) == 1


def test_load_next_job_index_resets_when_csv_changes(tmp_path):
    csv_path = tmp_path / "suitable.csv"
    _write_csv(csv_path, [{"id": "1", "link": "https://example.com/1"}])
    save_next_job_index(str(csv_path), 1)

    _write_csv(csv_path, [{"id": "2", "link": "https://example.com/2"}])

    assert load_next_job_index(str(csv_path), total_jobs=3) == 0


def test_load_next_job_index_clamps_to_total_jobs(tmp_path):
    csv_path = tmp_path / "suitable.csv"
    _write_csv(csv_path, [{"id": "1", "link": "https://example.com/1"}])
    save_next_job_index(str(csv_path), 99)

    assert load_next_job_index(str(csv_path), total_jobs=2) == 2


def test_advance_node_persists_next_job_index(tmp_path):
    csv_path = tmp_path / "suitable.csv"
    _write_csv(csv_path, [{"id": "1", "link": "https://example.com/1"}])

    result = advance_node({
        "csv_path": str(csv_path),
        "current_job_index": 2,
        "jobs": [],
    })

    with open(progress_path(str(csv_path)), encoding="utf-8") as f:
        progress = json.load(f)

    assert result["current_job_index"] == 3
    assert progress["next_job_index"] == 3
