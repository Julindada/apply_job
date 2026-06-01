import logging

from apply_job.cli import (
    _DEFAULT_APPLY_THREAD_ID,
    _configure_apply_logging,
    _resolve_apply_thread_id,
)


def test_apply_thread_id_defaults_to_stable_value():
    assert _resolve_apply_thread_id(None) == _DEFAULT_APPLY_THREAD_ID


def test_apply_thread_id_can_be_overridden():
    assert _resolve_apply_thread_id("custom-thread") == "custom-thread"


def test_configure_apply_logging_writes_to_file(tmp_path):
    log_path = tmp_path / "apply.log"

    resolved_log_path = _configure_apply_logging(str(log_path))
    logging.getLogger("test").info("agent log line")

    assert resolved_log_path == str(log_path)
    assert logging.getLogger().level == logging.INFO
    assert "agent log line" in log_path.read_text()
