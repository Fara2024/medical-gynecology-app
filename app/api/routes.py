from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

from app.core.gynecology_session import GynecologySession
from app.core.pregnancy_session import PregnancySession

SESSIONS_DIR = "data/sessions"

router = APIRouter(prefix="/api", tags=["medical-ai"])


# -----------------------------
# Schemas
# -----------------------------
class CreateSessionRequest(BaseModel):
    session_id: str


class MessageRequest(BaseModel):
    message: str


# -----------------------------
# Gynecology routes
# -----------------------------
@router.post("/gynecology/start")
def start_gynecology(req: CreateSessionRequest):
    session = GynecologySession(req.session_id)

    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f"{req.session_id}.json")
    session.save_to_file(path)

    return {
        "session_id": req.session_id,
        "question": session.get_current_question()
    }


@router.post("/gynecology/{session_id}/message")
def gynecology_message(session_id: str, req: MessageRequest):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Session not found")

    session = GynecologySession.load_from_file(path)
    reply = session.submit_answer("free_text", req.message)
    session.save_to_file(path)

    return {
        "reply": reply,
        "pregnancy_suspicion": session.pregnancy_suspicion
    }


# -----------------------------
# Transfer to pregnancy
# -----------------------------
@router.post("/gynecology/{session_id}/transfer")
def transfer_to_pregnancy(session_id: str):
    gyn_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(gyn_path):
        raise HTTPException(404, "Gynecology session not found")

    pregnancy_session = PregnancySession.from_gynecology_session(
        gyn_path,
        ollama_base_url="http://localhost:11434"
    )

    pregnancy_path = os.path.join(SESSIONS_DIR, f"{pregnancy_session.session_id}.json")
    pregnancy_session.save_to_file(pregnancy_path)

    first_q = pregnancy_session.start()

    return {
        "pregnancy_session_id": pregnancy_session.session_id,
        "first_question": first_q
    }


# -----------------------------
# Pregnancy routes
# -----------------------------
@router.post("/pregnancy/{session_id}/message")
def pregnancy_message(session_id: str, req: MessageRequest):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Pregnancy session not found")

    session = PregnancySession.load_from_file(path)
    reply = session.submit_answer(req.message)
    session.save_to_file(path)

    return {
        "reply": reply,
        "status": session.status.value
    }
