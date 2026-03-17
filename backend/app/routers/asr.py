import base64
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.models.schemas import AudioTranscriptionRequest, AudioTranscriptionResponse
from app.services.asr_service import ASRService
from app.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asr", tags=["ASR"])

_asr_service: ASRService | None = None
_dataset_service: DatasetService | None = None


def get_asr_service(settings: Annotated[Settings, Depends(get_settings)]) -> ASRService:
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService(model_size=settings.whisper_model_size)
    return _asr_service


def get_dataset_service(settings: Annotated[Settings, Depends(get_settings)]) -> DatasetService:
    global _dataset_service
    if _dataset_service is None:
        _dataset_service = DatasetService(data_dir=settings.data_dir)
    return _dataset_service


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    language: str = Form(default="en"),
    expected_text: str = Form(default=""),
    settings: Settings = Depends(get_settings),
    asr: ASRService = Depends(get_asr_service),
    dataset: DatasetService = Depends(get_dataset_service),
):
    if not session_id:
        session_id = str(uuid.uuid4())

    content_length = int(file.size or 0)
    if content_length > settings.max_audio_size_bytes:
        raise HTTPException(status_code=413, detail="Audio file exceeds size limit")

    audio_bytes = await file.read()
    if len(audio_bytes) > settings.max_audio_size_bytes:
        raise HTTPException(status_code=413, detail="Audio file exceeds size limit")

    try:
        response = await asr.transcribe_audio(
            audio_bytes=audio_bytes,
            language=language,
            session_id=session_id,
            expected_text=expected_text or None,
        )
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription error: {exc}") from exc

    dataset.log_interaction(
        session_id=session_id,
        audio_path=file.filename or "upload",
        transcript=response.transcript,
        expected_text=expected_text or None,
        wer=response.wer,
        language=language,
    )
    dataset.log_latency(response.processing_time_ms)
    return response


@router.post("/transcribe-base64", response_model=AudioTranscriptionResponse)
async def transcribe_base64(
    request: AudioTranscriptionRequest,
    audio_data: str,
    settings: Settings = Depends(get_settings),
    asr: ASRService = Depends(get_asr_service),
    dataset: DatasetService = Depends(get_dataset_service),
):
    try:
        audio_bytes = base64.b64decode(audio_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data") from exc

    if len(audio_bytes) > settings.max_audio_size_bytes:
        raise HTTPException(status_code=413, detail="Audio file exceeds size limit")

    try:
        response = await asr.transcribe_audio(
            audio_bytes=audio_bytes,
            language=request.language,
            session_id=request.session_id,
            expected_text=request.expected_text,
        )
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription error: {exc}") from exc

    dataset.log_interaction(
        session_id=request.session_id,
        audio_path="base64_upload",
        transcript=response.transcript,
        expected_text=request.expected_text,
        wer=response.wer,
        language=request.language,
    )
    return response


@router.get("/models")
async def list_models(asr: ASRService = Depends(get_asr_service)):
    return {"models": asr.list_models(), "current": asr._model_size}


@router.post("/switch-model")
async def switch_model(
    model_size: str,
    asr: ASRService = Depends(get_asr_service),
):
    valid = asr.list_models()
    if model_size not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {valid}")
    asr.switch_model(model_size)
    return {"message": f"Switched to model: {model_size}"}
