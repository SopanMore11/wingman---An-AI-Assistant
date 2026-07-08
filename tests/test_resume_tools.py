import inspect
from pathlib import Path

import pytest

from src.agents.resumeTailor import _get_resume_tailor_model
from src.tools.resume_tools import (
    DEFAULT_RESUME_PATH,
    _resolve_path,
    apply_patches,
    read_resume,
)


def test_resume_agent_model_uses_resume_specific_setting(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_MODEL", "anthropic/test-resume-model")

    model = _get_resume_tailor_model()

    assert model.model == "anthropic/test-resume-model"


def test_read_resume_defaults_to_base_resume():
    parameters = inspect.signature(read_resume).parameters

    assert list(parameters)[0] == "resume_path"
    assert parameters["resume_path"].default == DEFAULT_RESUME_PATH
    assert DEFAULT_RESUME_PATH == "dataset/resume.tex"


def test_apply_patches_replaces_unique_text(tmp_path, monkeypatch):
    tex_file = tmp_path / "resume.tex"
    tex_file.write_text("Skills: Python\nExperience: Built an API", encoding="utf-8")

    monkeypatch.setattr("src.tools.resume_tools.REPO_ROOT", tmp_path)

    patch_text = """<<<<<<< SEARCH
Built an API
=======
Built a Python API
>>>>>>> REPLACE"""

    result = apply_patches(patch_text, resume_path="resume.tex")

    assert result["status"] == "success"
    assert result["patches_applied"] == 1
    assert result["failed_patches"] == []


def test_apply_patches_rejects_ambiguous_search_text(tmp_path, monkeypatch):
    tex_file = tmp_path / "resume.tex"
    tex_file.write_text("Python and Python", encoding="utf-8")

    monkeypatch.setattr("src.tools.resume_tools.REPO_ROOT", tmp_path)

    patch_text = """<<<<<<< SEARCH
Python
=======
Python 3
>>>>>>> REPLACE"""

    result = apply_patches(patch_text, resume_path="resume.tex")

    assert result["status"] == "error"
    assert "No patches matched" in result["message"]


def test_resolve_path_rejects_files_outside_repository():
    outside_path = Path.home() / "resume.tex"

    with pytest.raises(ValueError, match="inside the Wingman project"):
        _resolve_path(str(outside_path), {".tex"})
