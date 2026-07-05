import os

from src.agents.base_agent import BaseAgent
from src.services.llm_services import LLMServices
from src.tools.resume_tools import (
    DEFAULT_RESUME_TAILOR_MODEL,
    compile_resume_to_pdf,
    tailor_resume,
)
from src.utils import load_md_file


def _get_resume_tailor_model():
    """Build the resume specialist model independently from the global app model."""
    model_name = os.getenv(
        "RESUME_TAILOR_AGENT_MODEL",
        os.getenv("RESUME_TAILOR_MODEL", DEFAULT_RESUME_TAILOR_MODEL),
    )
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
        return [tailor_resume, compile_resume_to_pdf]


def build_resume_tailor_agent():
    return ResumeTailorAgent().agent
