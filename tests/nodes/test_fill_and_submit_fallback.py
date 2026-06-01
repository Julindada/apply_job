from apply_job.nodes.apply.fill_and_submit import (
    _MAX_VALIDATION_RECOVERY_ATTEMPTS,
    _build_task,
    _build_validation_recovery_task,
    _parse_submission_status,
)


def test_parse_submission_status_detects_blocking_fields():
    status = _parse_submission_status(
        'Result: {"blocked": true, "fields": ["LinkedIn URL"], "message": "Required field"}'
    )

    assert status == {
        "blocked": True,
        "fields": ["LinkedIn URL"],
        "message": "Required field",
    }


def test_parse_submission_status_defaults_to_not_blocked_on_unparseable_output():
    status = _parse_submission_status("Submitted successfully")

    assert status["blocked"] is False
    assert status["fields"] == []


def test_validation_recovery_task_is_bounded_and_mentions_blocking_fields():
    task = _build_validation_recovery_task(
        job={"title": "Backend Engineer", "companyName": "Acme", "descriptionText": "Java"},
        resume_text="Java backend engineer",
        cover_letter_path=None,
        blocked_fields=["Work authorization", "LinkedIn URL"],
        next_link="https://example.com/next",
        attempt=1,
    )

    assert f"1/{_MAX_VALIDATION_RECOVERY_ATTEMPTS}" in task
    assert "Work authorization" in task
    assert "LinkedIn URL" in task
    assert "If the page is still blocked after this attempt, stop" in task


def test_fill_task_uses_existing_application_tab_before_next_job():
    task = _build_task(
        job={"title": "Backend Engineer", "companyName": "Acme", "descriptionText": "Java"},
        resume_text="Java backend engineer",
        cover_letter_path="/tmp/cover_letter_abc/cover_letter.pdf",
        required_fields=[],
        next_link="https://example.com/next",
    )

    assert "Do NOT click the LinkedIn apply button again" in task
    assert "Do NOT open a new application page" in task
    assert "switch to the existing application form tab" in task
    assert "Only after the application is submitted successfully" in task
