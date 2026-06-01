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


def test_configure_apply_logging_sets_info_level():
    _configure_apply_logging()

    assert logging.getLogger().level == logging.INFO
