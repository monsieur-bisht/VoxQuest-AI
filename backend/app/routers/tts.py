import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.config import Settings, get_settings
from app.models.schemas import TTSRequest, TTSResponse
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["TTS"])

_tts_service: TTSService | None = None


def get_tts_service(settings: Annotated[Settings, Depends(get_settings)]) -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService(
            engine_name=settings.tts_engine,
            data_dir=settings.data_dir,
        )
    return _tts_service


@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    tts: TTSService = Depends(get_tts_service),
):
    try:
        response = await tts.synthesize(
            text=request.text,
            language=request.language or "en",
            voice_id=request.voice_id or "",
        )
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc
    return response


@router.get("/synthesize/stream")
async def synthesize_stream(
    text: str,
    language: str = "en",
    tts: TTSService = Depends(get_tts_service),
):
    """Stream audio directly as MP3 bytes."""
    try:
        response = await tts.synthesize(text=text, language=language)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc

    file_path = tts.get_audio_path(Path(response.audio_url).name)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(iterfile(), media_type="audio/mpeg")


@router.get("/voices")
async def list_voices(tts: TTSService = Depends(get_tts_service)):
    return {"voices": tts.list_voices()}
