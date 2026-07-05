from pathlib import Path

from src.integrations import telegram


def test_extract_attachments_removes_marker_and_returns_pdf(monkeypatch):
    pdf_path = Path("dataset/resume_tailored.pdf")
    monkeypatch.setattr(telegram, "_resolve_attachment_path", lambda value: pdf_path)

    text, attachments = telegram._extract_attachments(
        "Your resume is ready. [[SEND_FILE:dataset/resume_tailored.pdf]]"
    )

    assert text == "Your resume is ready."
    assert attachments == [pdf_path]


def test_extract_attachments_discards_invalid_marker(monkeypatch):
    monkeypatch.setattr(telegram, "_resolve_attachment_path", lambda value: None)

    text, attachments = telegram._extract_attachments(
        "Done. [[SEND_FILE:../../credentials.json]]"
    )

    assert text == "Done."
    assert attachments == []
