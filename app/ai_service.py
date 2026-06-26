"""AI analysis service — API key is the only configuration users need."""

import base64
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openai import OpenAI

from app.prompts import CHAT_SYSTEM, HR_RECRUITER_SYSTEM

VISION_OCR_PROMPT = (
    "Extract every word of text from this resume page. "
    "Return only the raw resume text, preserving headings and bullet structure. "
    "Do not summarize or add commentary."
)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "No API key configured. Add your OpenAI API key in Settings (gear icon)."
        )
    return OpenAI(api_key=api_key)


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def extract_pdf_with_vision(file_path: Path, max_pages: int = 10) -> str:
    """OCR fallback for scanned or image-based PDFs using OpenAI vision."""
    import fitz

    doc = fitz.open(str(file_path))
    page_texts: List[str] = []

    try:
        for page_index in range(min(len(doc), max_pages)):
            page = doc[page_index]
            pixmap = page.get_pixmap(dpi=180)
            image_b64 = base64.b64encode(pixmap.tobytes("png")).decode("ascii")

            response = _client().chat.completions.create(
                model=_model(),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                temperature=0,
                max_tokens=4096,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                page_texts.append(text)
    finally:
        doc.close()

    return "\n\n".join(page_texts).strip()


def build_resume_context(resumes: List[Dict[str, str]], job_description: str) -> str:
    parts = []
    if job_description.strip():
        parts.append("=== JOB DESCRIPTION ===\n" + job_description.strip())
    else:
        parts.append(
            "=== JOB DESCRIPTION ===\n"
            "(None provided — evaluate against general professional standards.)"
        )

    for i, resume in enumerate(resumes, 1):
        parts.append(
            f"=== RESUME {i}: {resume['filename']} ===\n{resume['text']}"
        )
    return "\n\n".join(parts)


def rank_candidates(
    resumes: List[Dict[str, str]], job_description: str
) -> Tuple[str, List[Dict[str, Any]]]:
    context = build_resume_context(resumes, job_description)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": HR_RECRUITER_SYSTEM},
        {
            "role": "user",
            "content": (
                "Please analyze and rank all candidates below. "
                "Confirm you have parsed every resume, then provide your ranking.\n\n"
                + context
            ),
        },
    ]

    response = _client().chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=0.2,
    )
    assistant_message = response.choices[0].message.content or ""
    messages.append({"role": "assistant", "content": assistant_message})
    return assistant_message, messages


def chat(
    messages: List[Dict[str, Any]], user_message: str
) -> Tuple[str, List[Dict[str, Any]]]:
    history: List[Dict[str, Any]] = [{"role": "system", "content": CHAT_SYSTEM}]
    for msg in messages:
        if msg["role"] in ("user", "assistant"):
            history.append({"role": msg["role"], "content": msg["content"]})
    history.append({"role": "user", "content": user_message})

    response = _client().chat.completions.create(
        model=_model(),
        messages=history,
        temperature=0.3,
    )
    assistant_message = response.choices[0].message.content or ""
    history.append({"role": "assistant", "content": assistant_message})
    return assistant_message, history[1:]  # strip system prompt from stored history