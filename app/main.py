"""Talent Ranker — web app for non-technical HR screening."""

import os
import re
import shutil
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel

from app.ai_service import chat, extract_pdf_with_vision, rank_candidates
from app.resume_parser import SUPPORTED_EXTENSIONS, extract_text

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = Path(__file__).resolve().parent / "static"
ENV_FILE = BASE_DIR / ".env"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_BATCH = 20
MAX_SESSIONS = 50
READ_CHUNK_SIZE = 1024 * 1024

UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Talent Ranker", version="1.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory session store (sufficient for single-user / small-team local use)
sessions: OrderedDict[str, dict] = OrderedDict()


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^\w.\- ]", "_", base).strip(" .")
    return cleaned or "resume"


def _prune_sessions() -> None:
    while len(sessions) > MAX_SESSIONS:
        sessions.popitem(last=False)


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    total = 0
    with dest.open("wb") as f:
        while True:
            chunk = await upload.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                )
            f.write(chunk)


class SettingsRequest(BaseModel):
    api_key: str
    model: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return {
        "configured": bool(key),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


@app.post("/api/settings")
async def save_settings(body: SettingsRequest):
    lines = [f"OPENAI_API_KEY={body.api_key.strip()}"]
    if body.model:
        lines.append(f"OPENAI_MODEL={body.model.strip()}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    load_dotenv(override=True)
    os.environ["OPENAI_API_KEY"] = body.api_key.strip()
    if body.model:
        os.environ["OPENAI_MODEL"] = body.model.strip()
    return {"ok": True}


@app.post("/api/analyze")
async def analyze(
    resumes: list[UploadFile] = File(...),
    job_description: str = Form(""),
):
    if not resumes:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one resume.",
        )
    if len(resumes) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Upload at most {MAX_FILES_PER_BATCH} resumes per batch.",
        )

    parsed: List[dict] = []
    session_dir = UPLOAD_DIR / str(uuid.uuid4())
    session_dir.mkdir()

    try:
        for upload in resumes:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported file: {upload.filename}. "
                        f"Use {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
                    ),
                )

            safe_name = _safe_filename(upload.filename or f"resume{suffix}")
            dest = session_dir / safe_name
            await _save_upload(upload, dest)

            ocr_fallback = None
            if suffix == ".pdf" and os.getenv("OPENAI_API_KEY", "").strip():
                ocr_fallback = extract_pdf_with_vision
            try:
                text = extract_text(dest, pdf_ocr_fallback=ocr_fallback)
            except (RuntimeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=str(e)) from e

            if not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Could not read text from {safe_name}. "
                        "Ensure the PDF contains selectable text or configure your "
                        "OpenAI API key in Settings for scanned-document support."
                    ),
                )
            parsed.append({"filename": safe_name, "text": text})

        result, messages = rank_candidates(parsed, job_description)
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": messages,
            "resumes": parsed,
            "job_description": job_description,
        }
        _prune_sessions()
        return {
            "session_id": session_id,
            "result": result,
            "resume_count": len(parsed),
        }
    except HTTPException:
        raise
    except (RuntimeError, OpenAIError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"File error: {e}") from e
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


@app.post("/api/chat")
async def chat_endpoint(body: ChatRequest):
    session = sessions.get(body.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session expired. Please run a new analysis.",
        )

    try:
        reply, updated = chat(session["messages"], body.message.strip())
        session["messages"] = updated
        sessions.move_to_end(body.session_id)
        return {"reply": reply}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OpenAIError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e