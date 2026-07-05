"""Tools for tailoring LaTeX resumes to a job description."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from openai import OpenAI

from src.config.settings import REPO_ROOT

DEFAULT_RESUME_TAILOR_API_BASE = "https://lightning.ai/api/v1/"
DEFAULT_RESUME_TAILOR_MODEL = "anthropic/claude-haiku-4-5-20251001"
DEFAULT_RESUME_PATH = "dataset/resume.tex"
MAX_INPUT_BYTES = 1_000_000
MAX_JOB_DESCRIPTION_CHARS = 100_000

SYSTEM_PROMPT = r"""You are an expert ATS resume optimization engine and technical recruiter
with deep knowledge of how ATS parsers (Workday, Greenhouse, Taleo, iCIMS) score resumes.

You will be given a candidate's resume in LaTeX and a target job description (JD).

Instead of rewriting the whole file, output a series of SEARCH/REPLACE edits: the minimum
set of changes needed to tailor the resume to the JD. Do not touch anything you do not need to.

HARD RULES:
- Never touch \href{...}{...} commands, contact info, dates, company names, degree names,
  GPA, or section headers.
- Never invent a tool, framework, metric, or outcome not already present in the resume, or a
  reasonable synonym or umbrella term for something already there.
- You may reword bullets to mirror JD terminology where the underlying work already supports
  it, reorder items within the Skills section, and add skill names only if they are true
  synonyms or aliases of something already in the resume.
- Each SEARCH block must be an exact, verbatim substring of the source file, including LaTeX
  commands, braces, and whitespace.
- Keep each SEARCH block as short as possible while still being unique in the file.

Return only blocks in this exact format, with no commentary:

<<<<<<< SEARCH
exact original text
=======
replacement text
>>>>>>> REPLACE
"""

USER_TEMPLATE = """BASE RESUME (.tex):
-----
{resume}
-----

TARGET JOB DESCRIPTION:
-----
{jd}
-----

Return only SEARCH/REPLACE blocks per the system rules."""

BLOCK_RE = re.compile(
    r"<{7}\s*SEARCH\s*\r?\n(.*?)\r?\n={7}\s*\r?\n(.*?)\r?\n>{7}\s*REPLACE",
    re.DOTALL,
)


def _resolve_path(file_path: str, allowed_suffixes: set[str]) -> Path:
    """Resolve a user path and keep file access inside the repository."""
    candidate = Path(file_path).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    candidate = candidate.resolve()

    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Resume files must be inside the Wingman project directory.") from exc

    if candidate.suffix.lower() not in allowed_suffixes:
        suffixes = ", ".join(sorted(allowed_suffixes))
        raise ValueError(f"Expected one of these file types: {suffixes}")
    return candidate


def _read_input(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"Input file is larger than {MAX_INPUT_BYTES} bytes: {path}")
    return path.read_text(encoding="utf-8")


def apply_resume_patches(original: str, patch_text: str) -> tuple[str, int, list[str]]:
    """Apply unique SEARCH/REPLACE blocks to resume text."""
    blocks = BLOCK_RE.findall(patch_text)
    if not blocks:
        raise ValueError("No SEARCH/REPLACE blocks found in model output.")

    result = original
    applied = 0
    failed: list[str] = []
    for search, replacement in blocks:
        count = result.count(search)
        if count == 0:
            failed.append(f"[NOT FOUND] {search[:80]}")
            continue
        if count > 1:
            failed.append(f"[AMBIGUOUS, {count} matches] {search[:80]}")
            continue
        result = result.replace(search, replacement, 1)
        applied += 1

    return result, applied, failed


def tailor_resume(
    job_description: str,
    resume_path: str = DEFAULT_RESUME_PATH,
    output_path: str = "",
) -> dict:
    """Tailor a LaTeX resume from a chat-provided job description and create a PDF.

    Args:
        job_description: Complete job description text supplied by the user in chat.
        resume_path: Source .tex resume. Defaults to dataset/resume.tex.
        output_path: Optional output .tex path. Defaults beside the source resume.

    Returns:
        A status dictionary with output paths, patch counts, and a Telegram file marker.
    """
    try:
        source_path = _resolve_path(resume_path, {".tex"})
        if output_path:
            destination = _resolve_path(output_path, {".tex"})
        else:
            destination = source_path.with_name(f"{source_path.stem}_tailored.tex")

        if destination == source_path:
            raise ValueError("Output path must not overwrite the source resume.")

        resume_content = _read_input(source_path)
        jd_content = job_description.strip()
        if not jd_content:
            raise ValueError("The job description text cannot be empty.")
        if len(jd_content) > MAX_JOB_DESCRIPTION_CHARS:
            raise ValueError(
                f"Job description is longer than {MAX_JOB_DESCRIPTION_CHARS} characters."
            )
        api_key = os.getenv("LIGHTNING_API_KEY")
        if not api_key:
            raise RuntimeError("Missing required environment variable: LIGHTNING_API_KEY")

        client = OpenAI(
            base_url=os.getenv(
                "RESUME_TAILOR_API_BASE",
                os.getenv("LITAI_API_BASE", DEFAULT_RESUME_TAILOR_API_BASE),
            ),
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=os.getenv("RESUME_TAILOR_MODEL", DEFAULT_RESUME_TAILOR_MODEL),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        resume=resume_content,
                        jd=jd_content,
                    ),
                },
            ],
            temperature=0.2,
        )
        patch_text = response.choices[0].message.content or ""
        tailored, applied, failed = apply_resume_patches(resume_content, patch_text.strip())
        total = len(BLOCK_RE.findall(patch_text))

        if applied == 0:
            raise ValueError("The model returned patches, but none matched the source resume.")
        if tailored.count("{") != tailored.count("}"):
            raise ValueError("Tailored LaTeX has mismatched braces; output was not saved.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(tailored, encoding="utf-8")
        result = {
            "status": "success",
            "output_path": str(destination),
            "patches_applied": applied,
            "patches_total": total,
            "failed_patches": failed,
        }
        pdf_result = compile_resume_to_pdf(str(destination))
        if pdf_result.get("status") == "success":
            result.update(pdf_result)
        else:
            result["status"] = "partial_success"
            result["pdf_error"] = pdf_result.get("message", "PDF compilation failed.")
        return result
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def compile_resume_to_pdf(tex_path: str, output_directory: str = "") -> dict:
    """Compile a tailored LaTeX resume to PDF with two pdflatex passes.

    Args:
        tex_path: Path to a .tex file inside the project directory.
        output_directory: Optional output directory inside the project.

    Returns:
        A status dictionary containing the generated PDF path.
    """
    try:
        source_path = _resolve_path(tex_path, {".tex"})
        if not source_path.is_file():
            raise FileNotFoundError(f"File not found: {source_path}")
        if shutil.which("pdflatex") is None:
            raise RuntimeError(
                "pdflatex was not found. Install MiKTeX or another LaTeX distribution."
            )

        if output_directory:
            output_dir = _resolve_path(
                str(Path(output_directory) / "placeholder.pdf"), {".pdf"}
            ).parent
        else:
            output_dir = source_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        for pass_number in range(1, 3):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    str(output_dir),
                    source_path.name,
                ],
                cwd=source_path.parent,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                log_tail = result.stdout[-3000:]
                raise RuntimeError(
                    f"pdflatex failed on pass {pass_number}:\n{log_tail}"
                )

        pdf_path = output_dir / f"{source_path.stem}.pdf"
        if not pdf_path.is_file():
            raise RuntimeError("pdflatex succeeded but did not create a PDF.")

        for suffix in (".aux", ".log", ".out"):
            auxiliary = output_dir / f"{source_path.stem}{suffix}"
            auxiliary.unlink(missing_ok=True)

        return {
            "status": "success",
            "pdf_path": str(pdf_path),
            "attachment_marker": f"[[SEND_FILE:{pdf_path}]]",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
