from types import SimpleNamespace

from src.agents.expenseManager import _build_expense_instruction
from src.agents.wingman_runtime import (
    _extract_attachment_markers,
    _build_orchestrator_instruction,
    _extract_final_response_text,
)


def test_extract_final_response_text_ignores_thought_parts():
    parts = [
        SimpleNamespace(text="I should think first.", thought=True),
        SimpleNamespace(text="<b>Summary</b>\nTotal: <code>1200</code>", thought=False),
    ]

    result = _extract_final_response_text(parts)

    assert result == "<b>Summary</b>\nTotal: <code>1200</code>"


def test_extract_final_response_text_falls_back_when_only_thought_exists():
    parts = [
        SimpleNamespace(text="Fallback answer", thought=True),
    ]

    result = _extract_final_response_text(parts)

    assert result == "Fallback answer"


def test_extract_attachment_markers_reads_tool_response():
    parts = [
        SimpleNamespace(
            function_response=SimpleNamespace(
                response={
                    "status": "success",
                    "attachment_marker": "[[SEND_FILE:dataset/resume_tailored.pdf]]",
                }
            )
        )
    ]

    result = _extract_attachment_markers(parts)

    assert result == ["[[SEND_FILE:dataset/resume_tailored.pdf]]"]


def test_build_expense_instruction_includes_runtime_date_context():
    instruction = _build_expense_instruction()

    assert "Today is " in instruction
    assert "The first day of this month is " in instruction
    assert "For 'this month', use the first day of this month through today" in instruction


def test_orchestrator_routes_resume_tailoring_requests():
    instruction = _build_orchestrator_instruction()

    assert "delegate to the resume tailor agent" in instruction
    assert "default base resume is dataset/resume.tex" in instruction
    assert "do not request a JD file path" in instruction
    assert "Preserve every [[SEND_FILE:path]] marker" in instruction
