import os

from src.agents.base_agent import BaseAgent
from src.services.llm_services import LLMServices
from src.tools.resume_tools import (
    read_resume,
    apply_patches,
    compile_resume_to_pdf,
)
from src.utils import load_md_file

# Override with RESUME_TAILOR_MODEL env var to switch models without touching code.
DEFAULT_RESUME_TAILOR_MODEL = "anthropic/claude-haiku-4-5-20251001"


def _get_resume_tailor_model():
    model_name = os.getenv("RESUME_TAILOR_MODEL", DEFAULT_RESUME_TAILOR_MODEL)
    return LLMServices().get_litai_model(model_name=model_name)


class ResumeTailorAgent(BaseAgent):
    """Agent for tailoring LaTeX resumes to target job descriptions."""

    def __init__(self):
        super().__init__(
            name="resume_tailor_agent",
            description=(
                "Tailors an existing LaTeX resume to a target job description using "
                "truthful, minimal ATS-focused edits and can compile the result to PDF."
            ),
            instruction=load_md_file("skills/resume_tailor.md"),
            model=_get_resume_tailor_model(),
        )

    def _get_tools(self):
        return [read_resume, apply_patches, compile_resume_to_pdf]


def build_resume_tailor_agent():
    return ResumeTailorAgent().agent
