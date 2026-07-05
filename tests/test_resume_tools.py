import inspect
from pathlib import Path

import pytest

from src.agents.resumeTailor import _get_resume_tailor_model
from src.tools.resume_tools import (
    DEFAULT_RESUME_PATH,
    _resolve_path,
    apply_resume_patches,
    tailor_resume,
)


def test_resume_agent_model_uses_resume_specific_setting(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_MODEL", "anthropic/test-resume-model")
    monkeypatch.delenv("RESUME_TAILOR_AGENT_MODEL", raising=False)

    model = _get_resume_tailor_model()

    assert model.model == "anthropic/test-resume-model"


def test_tailor_resume_accepts_chat_jd_and_defaults_to_base_resume():
    parameters = inspect.signature(tailor_resume).parameters

    assert list(parameters)[:2] == ["job_description", "resume_path"]
    assert parameters["resume_path"].default == DEFAULT_RESUME_PATH
    assert DEFAULT_RESUME_PATH == "dataset/resume.tex"


def test_apply_resume_patches_replaces_unique_text():
    original = "Skills: Python\nExperience: Built an API"
    patches = """<<<<<<< SEARCH
Built an API
=======
Built a Python API
>>>>>>> REPLACE"""

    tailored, applied, failed = apply_resume_patches(original, patches)

    assert tailored == "Skills: Python\nExperience: Built a Python API"
    assert applied == 1
    assert failed == []


def test_apply_resume_patches_rejects_ambiguous_search_text():
    original = "Python and Python"
    patches = """<<<<<<< SEARCH
Python
=======
Python 3
>>>>>>> REPLACE"""

    tailored, applied, failed = apply_resume_patches(original, patches)

    assert tailored == original
    assert applied == 0
    assert failed == ["[AMBIGUOUS, 2 matches] Python"]


def test_resolve_path_rejects_files_outside_repository():
    outside_path = Path.home() / "resume.tex"

    with pytest.raises(ValueError, match="inside the Wingman project"):
        _resolve_path(str(outside_path), {".tex"})
