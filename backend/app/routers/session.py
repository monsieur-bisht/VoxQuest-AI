import logging
import uuid
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.models.schemas import DatasetEntry, SessionInfo, StoryState
from app.services.dataset_service import DatasetService
from app.services.story_service import StoryService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Session & Dataset"])

_sessions_store: dict[str, SessionInfo] = {}


def get_dataset_service(settings: Annotated[Settings, Depends(get_settings)]) -> DatasetService:
    from app.routers.asr import get_dataset_service as _ds
    return _ds(settings)


def get_story_service(settings: Annotated[Settings, Depends(get_settings)]) -> StoryService:
    from app.routers.story import get_story_service as _ss
    return _ss(settings)


@router.post("/api/session/create", response_model=SessionInfo)
async def create_session(
    character_name: str = "Adventurer",
    story: StoryService = Depends(get_story_service),
):
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    story.reset_session(session_id)
    state = story.get_or_create_session(session_id)
    state.character_name = character_name
    story.save_session(session_id)

    info = SessionInfo(
        session_id=session_id,
        created_at=now,
        last_active=now,
        story_state=state,
    )
    _sessions_store[session_id] = info
    return info


@router.get("/api/session/list", response_model=List[SessionInfo])
async def list_sessions(story: StoryService = Depends(get_story_service)):
    persisted = story.list_sessions()
    sessions = []
    for s in persisted:
        sid = s["session_id"]
        if sid in _sessions_store:
            sessions.append(_sessions_store[sid])
        else:
            state = story.load_session(sid)
            now = datetime.utcnow()
            info = SessionInfo(
                session_id=sid,
                created_at=now,
                last_active=now,
                story_state=state,
            )
            sessions.append(info)
    return sessions


@router.get("/api/session/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    if session_id in _sessions_store:
        info = _sessions_store[session_id]
        state = story.get_or_create_session(session_id)
        info.story_state = state
        info.last_active = datetime.utcnow()
        return info

    state = story.load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    now = datetime.utcnow()
    info = SessionInfo(
        session_id=session_id,
        created_at=now,
        last_active=now,
        story_state=state,
    )
    _sessions_store[session_id] = info
    return info


@router.delete("/api/session/{session_id}")
async def delete_session(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    _sessions_store.pop(session_id, None)
    story.delete_session(session_id)
    return {"message": f"Session '{session_id}' deleted"}


@router.get("/api/dataset/entries", response_model=List[DatasetEntry])
async def list_dataset_entries(
    session_id: str | None = Query(default=None),
    language: str | None = Query(default=None),
    dataset: DatasetService = Depends(get_dataset_service),
):
    filters = {}
    if session_id:
        filters["session_id"] = session_id
    if language:
        filters["language"] = language
    return dataset.get_entries(filters or None)


@router.get("/api/dataset/export")
async def export_dataset(
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
    dataset: DatasetService = Depends(get_dataset_service),
):
    data = dataset.export_dataset(fmt=fmt)
    media_type = "text/csv" if fmt == "csv" else "application/json"
    filename = f"dataset.{fmt}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
