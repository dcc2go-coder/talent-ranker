"""Talent Ranker — web app for non-technical HR screening."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai_service import chat, extract_pdf_with_vision, rank_candidates
from app.resume_parser import SUPPORTED_EXTENSIONS, extract_text

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = Path(__file__).resolve().parent / "static"
ENV_FILE = BASE_DIR / ".env"

UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Talent Ranker", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory session store (sufficient for single-user / small-team local use)
sessions: Dict[str, dict] = {}


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
        raise HTTPException(400, "Upload at least one resume.")

    parsed: List[dict] = []
    session_dir = UPLOAD_DIR / str(uuid.uuid4())
    session_dir.mkdir()

    try:
        for upload in resumes:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    400,
                    f"Unsupported file: {upload.filename}. "
                    f"Use {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
                )

            dest = session_dir / (upload.filename or f"resume{suffix}")
            with dest.open("wb") as f:
                shutil.copyfileobj(upload.file, f)

            ocr_fallback = None
            if suffix == ".pdf" and os.getenv("OPENAI_API_KEY", "").strip():
                ocr_fallback = extract_pdf_with_vision
            try:
                text = extract_text(dest, pdf_ocr_fallback=ocr_fallback)
            except RuntimeError as e:
                raise HTTPException(400, str(e)) from e

            if not text.strip():
                raise HTTPException(
                    400,
                    f"Could not read text from {upload.filename}. "
                    "Ensure the PDF contains selectable text or configure your "
                    "OpenAI API key in Settings for scanned-document support.",
                )
            parsed.append({"filename": upload.filename or dest.name, "text": text})

        result, messages = rank_candidates(parsed, job_description)
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": messages,
            "resumes": parsed,
            "job_description": job_description,
        }
        return {
            "session_id": session_id,
            "result": result,
            "resume_count": len(parsed),
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}") from e
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


@app.post("/api/chat")
async def chat_endpoint(body: ChatRequest):
    session = sessions.get(body.session_id)
    if not session:
        raise HTTPException(404, "Session expired. Please run a new analysis.")

    try:
        reply, updated = chat(session["messages"], body.message.strip())
        session["messages"] = updated
        return {"reply": reply}
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}") from e