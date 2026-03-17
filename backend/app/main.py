from __future__ import annotations

import base64
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .metrics import word_error_rate
from .storage import (
    export_dataset_csv,
    export_dataset_json,
    fetch_session,
    init_db,
    insert_benchmark,
    insert_dataset_entry,
    insert_speech_sample,
    upsert_session,
)
from .story_engine import advance_scene, detect_language_mode, get_scene, list_choices, tone_modifier


class StartGameResponse(BaseModel):
    session_id: str
    scene_id: str
    narration: str
    choices: List[str]
    relationship_score: int
    emotion: str
    tts: Dict[str, float]


class TurnRequest(BaseModel):
    session_id: str
    transcript: str = Field(min_length=1)
    expected_transcript: Optional[str] = None
    confidence: float = 0.85
    noise_level: Optional[str] = "medium"
    accent_tag: Optional[str] = "neutral"


class SaveLoadRequest(BaseModel):
    session_id: str


class DatasetTagRequest(BaseModel):
    session_id: str
    transcript: str
    language_tag: str
    noise_level: str
    accent_tag: str
    anonymized_audio_id: Optional[str] = None


app = FastAPI(title="VoxQuest-AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def default_session(session_id: str) -> Dict[str, Any]:
    return {
        "id": session_id,
        "current_scene": "start",
        "relationship_score": 0,
        "decisions": [],
        "updated_at": utc_now(),
    }


def session_or_404(session_id: str) -> Dict[str, Any]:
    session = fetch_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/game/start", response_model=StartGameResponse)
def start_game() -> StartGameResponse:
    session_id = str(uuid.uuid4())
    session = default_session(session_id)
    upsert_session(
        {
            "id": session["id"],
            "current_scene": session["current_scene"],
            "relationship_score": session["relationship_score"],
            "decisions_json": json.dumps(session["decisions"]),
            "updated_at": session["updated_at"],
        }
    )
    scene = get_scene("start")
    return StartGameResponse(
        session_id=session_id,
        scene_id=scene.scene_id,
        narration=scene.narration,
        choices=list_choices(scene.scene_id),
        relationship_score=0,
        emotion=scene.emotion,
        tts=tone_modifier(scene.emotion),
    )


@app.post("/api/speech/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language_hint: str = Form("auto"),
    noise_level: str = Form("medium"),
    accent_tag: str = Form("neutral"),
    transcript_override: Optional[str] = Form(None),
) -> Dict[str, Any]:
    raw = await audio.read()
    size_hint = len(raw)

    fallback_transcript = os.getenv("VOXQUEST_ASR_FALLBACK_TEXT", "Proceed to the next scene")
    if transcript_override:
        transcript = transcript_override.strip()
    else:
        transcript = fallback_transcript if size_hint > 0 else "Audio not detected"

    language_mode = detect_language_mode(transcript)
    confidence = max(0.4, min(0.98, 0.9 - (0.1 if noise_level == "high" else 0.0)))

    sample_preview = base64.b64encode(raw[:48]).decode("ascii") if raw else ""
    insert_speech_sample(
        {
            "session_id": session_id,
            "transcript": transcript,
            "audio_b64": base64.b64encode(raw).decode("ascii"),
            "language_mode": language_mode,
            "noise_level": noise_level,
            "accent_tag": accent_tag,
            "created_at": utc_now(),
        }
    )

    return {
        "transcript": transcript,
        "confidence": round(confidence, 3),
        "language_hint": language_hint,
        "language_mode": language_mode,
        "noise_level": noise_level,
        "accent_tag": accent_tag,
        "sample_preview_b64": sample_preview,
    }


@app.post("/api/game/turn")
def game_turn(payload: TurnRequest) -> Dict[str, Any]:
    started = time.perf_counter()
    session = session_or_404(payload.session_id)

    next_scene = advance_scene(session["current_scene"], payload.transcript)
    decisions = list(session["decisions"])
    decisions.append(
        {
            "from": session["current_scene"],
            "input": payload.transcript,
            "to": next_scene.scene_id,
            "timestamp": utc_now(),
        }
    )

    relationship_score = session["relationship_score"] + next_scene.relationship_delta
    updated = {
        "id": session["id"],
        "current_scene": next_scene.scene_id,
        "relationship_score": relationship_score,
        "decisions": decisions,
        "updated_at": utc_now(),
    }

    upsert_session(
        {
            "id": updated["id"],
            "current_scene": updated["current_scene"],
            "relationship_score": updated["relationship_score"],
            "decisions_json": json.dumps(updated["decisions"]),
            "updated_at": updated["updated_at"],
        }
    )

    wer = None
    if payload.expected_transcript:
        wer = round(word_error_rate(payload.expected_transcript, payload.transcript), 4)

    latency_ms = (time.perf_counter() - started) * 1000
    language_mode = detect_language_mode(payload.transcript)

    insert_benchmark(
        {
            "session_id": payload.session_id,
            "transcript": payload.transcript,
            "expected_transcript": payload.expected_transcript,
            "confidence": payload.confidence,
            "wer": wer,
            "latency_ms": latency_ms,
            "language_mode": language_mode,
            "noise_level": payload.noise_level,
            "accent_tag": payload.accent_tag,
            "created_at": utc_now(),
        }
    )

    return {
        "scene_id": next_scene.scene_id,
        "narration": next_scene.narration,
        "choices": list_choices(next_scene.scene_id),
        "emotion": next_scene.emotion,
        "relationship_score": relationship_score,
        "tts": tone_modifier(next_scene.emotion),
        "benchmark": {
            "wer": wer,
            "confidence": payload.confidence,
            "latency_ms": round(latency_ms, 2),
            "language_mode": language_mode,
        },
    }


@app.post("/api/game/save")
def save_game(payload: SaveLoadRequest) -> Dict[str, str]:
    session_or_404(payload.session_id)
    return {"status": "saved", "session_id": payload.session_id}


@app.post("/api/game/load")
def load_game(payload: SaveLoadRequest) -> Dict[str, Any]:
    session = session_or_404(payload.session_id)
    scene = get_scene(session["current_scene"])
    return {
        "session_id": session["id"],
        "scene_id": scene.scene_id,
        "narration": scene.narration,
        "choices": list_choices(scene.scene_id),
        "relationship_score": session["relationship_score"],
        "decisions": session["decisions"],
        "emotion": scene.emotion,
        "tts": tone_modifier(scene.emotion),
    }


@app.post("/api/dataset/tag")
def tag_dataset(payload: DatasetTagRequest) -> Dict[str, Any]:
    session_or_404(payload.session_id)
    insert_dataset_entry(
        {
            "session_id": payload.session_id,
            "transcript": payload.transcript,
            "language_tag": payload.language_tag,
            "noise_level": payload.noise_level,
            "accent_tag": payload.accent_tag,
            "anonymized_audio_id": payload.anonymized_audio_id,
            "created_at": utc_now(),
        }
    )
    return {"status": "tagged"}


@app.get("/api/dataset/export")
def export_dataset(format: str = "json") -> Any:
    if format == "csv":
        return PlainTextResponse(export_dataset_csv(), media_type="text/csv")
    if format == "json":
        return JSONResponse(export_dataset_json())
    raise HTTPException(status_code=400, detail="Unsupported format")
