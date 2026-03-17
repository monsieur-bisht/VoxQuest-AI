import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.schemas import StoryNarration, StoryState
from app.services.story_service import StoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/story", tags=["Story"])

_story_service: StoryService | None = None


def get_story_service(settings: Annotated[Settings, Depends(get_settings)]) -> StoryService:
    global _story_service
    if _story_service is None:
        _story_service = StoryService(
            stories_dir="./stories",
            data_dir=settings.data_dir,
        )
    return _story_service


@router.post("/start", response_model=StoryNarration)
async def start_story(
    session_id: str = "",
    character_name: str = "Adventurer",
    story: StoryService = Depends(get_story_service),
):
    if not session_id:
        session_id = str(uuid.uuid4())
    story.reset_session(session_id)
    state = story.get_or_create_session(session_id)
    state.character_name = character_name
    story.save_session(session_id)
    narration = story.get_current_narration(session_id)
    return narration


@router.post("/choice", response_model=StoryNarration)
async def make_choice(
    session_id: str,
    choice_id: str,
    story: StoryService = Depends(get_story_service),
):
    try:
        return story.process_choice(session_id=session_id, choice_id=choice_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Story choice error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/state/{session_id}", response_model=StoryState)
async def get_state(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    state = story.get_or_create_session(session_id)
    return state


@router.post("/save/{session_id}")
async def save_game(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    story.save_session(session_id)
    return {"message": f"Session {session_id} saved"}


@router.post("/load/{session_id}", response_model=StoryState)
async def load_game(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    state = story.load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return state


@router.post("/reset/{session_id}", response_model=StoryNarration)
async def reset_game(
    session_id: str,
    story: StoryService = Depends(get_story_service),
):
    story.reset_session(session_id)
    return story.get_current_narration(session_id)
