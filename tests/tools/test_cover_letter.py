import os

from apply_job.tools.cover_letter import _write_pdf


def test_cover_letter_pdf_uses_stable_upload_filename():
    path = _write_pdf("Dear Hiring Manager,\nHello.", "job-123")

    try:
        assert os.path.basename(path) == "cover_letter.pdf"
        assert os.path.exists(path)
    finally:
        os.unlink(path)
        os.rmdir(os.path.dirname(path))
