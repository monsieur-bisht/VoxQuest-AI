import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.models.schemas import StoryChoice, StoryNarration, StoryState

logger = logging.getLogger(__name__)


class StoryService:
    def __init__(self, stories_dir: str = "./stories", data_dir: str = "./data"):
        self._stories_dir = Path(stories_dir)
        self._sessions_dir = Path(data_dir) / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._story_data: Dict[str, Any] = {}
        self._sessions: Dict[str, StoryState] = {}
        self._load_stories()

    def _load_stories(self):
        story_file = self._stories_dir / "forest_adventure.json"
        if story_file.exists():
            try:
                with open(story_file, "r", encoding="utf-8") as f:
                    self._story_data = json.load(f)
                logger.info("Loaded story: %s", self._story_data.get("title"))
            except Exception as exc:
                logger.error("Failed to load story file: %s", exc)
                self._story_data = self._default_story()
        else:
            self._story_data = self._default_story()

    def _default_story(self) -> Dict[str, Any]:
        return {
            "story_id": "default",
            "title": "A Simple Adventure",
            "start_node": "start",
            "nodes": {
                "start": {
                    "node_id": "start",
                    "narration": "Your adventure begins. A crossroads lies ahead.",
                    "emotional_tone": "neutral",
                    "choices": [
                        {"choice_id": "north", "text": "Go north", "consequence_preview": "Head forward"},
                        {"choice_id": "south", "text": "Go south", "consequence_preview": "Turn back"},
                    ],
                    "effects": {},
                    "is_ending": False,
                },
                "north": {
                    "node_id": "north",
                    "narration": "You head north and find a treasure chest. Victory is yours!",
                    "emotional_tone": "triumphant",
                    "choices": [],
                    "effects": {},
                    "is_ending": True,
                },
                "south": {
                    "node_id": "south",
                    "narration": "You head south and return home safely. Another day awaits.",
                    "emotional_tone": "peaceful",
                    "choices": [],
                    "effects": {},
                    "is_ending": True,
                },
            },
        }

    def _get_node(self, node_id: str) -> Dict[str, Any]:
        nodes = self._story_data.get("nodes", {})
        node = nodes.get(node_id)
        if node is None:
            start = self._story_data.get("start_node", "start")
            node = nodes.get(start, {})
        return node

    def _apply_effects(self, state: StoryState, effects: Dict[str, Any]) -> StoryState:
        if not effects:
            return state
        if "health" in effects:
            state.health = max(0, min(100, state.health + effects["health"]))
        if "relationship_score" in effects:
            state.relationship_score = max(
                0, min(100, state.relationship_score + effects["relationship_score"])
            )
        if "inventory_add" in effects:
            item = effects["inventory_add"]
            if item not in state.inventory:
                state.inventory.append(item)
        if "inventory_remove" in effects:
            item = effects["inventory_remove"]
            if item in state.inventory:
                state.inventory.remove(item)
        return state

    def _node_to_narration(self, node: Dict[str, Any]) -> StoryNarration:
        choices = [
            StoryChoice(
                choice_id=c["choice_id"],
                text=c["text"],
                consequence_preview=c.get("consequence_preview"),
            )
            for c in node.get("choices", [])
        ]
        return StoryNarration(
            narration_text=node.get("narration", ""),
            choices=choices,
            node_id=node.get("node_id", "start"),
            emotional_tone=node.get("emotional_tone", "neutral"),
            is_ending=node.get("is_ending", False),
        )

    def get_or_create_session(self, session_id: str) -> StoryState:
        if session_id in self._sessions:
            return self._sessions[session_id]
        session_file = self._sessions_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = StoryState(**data)
                self._sessions[session_id] = state
                return state
            except Exception as exc:
                logger.warning("Failed to load session %s: %s", session_id, exc)
        start_node = self._story_data.get("start_node", "start")
        state = StoryState(session_id=session_id, current_node_id=start_node)
        state.visited_nodes.append(start_node)
        self._sessions[session_id] = state
        self.save_session(session_id)
        return state

    def get_current_narration(self, session_id: str) -> StoryNarration:
        state = self.get_or_create_session(session_id)
        node = self._get_node(state.current_node_id)
        return self._node_to_narration(node)

    def process_choice(self, session_id: str, choice_id: str) -> StoryNarration:
        state = self.get_or_create_session(session_id)
        current_node = self._get_node(state.current_node_id)

        valid_ids = {c["choice_id"] for c in current_node.get("choices", [])}
        if choice_id not in valid_ids:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid choice '{choice_id}' for node '{state.current_node_id}'",
            )

        state.story_log.append(
            {
                "node_id": state.current_node_id,
                "choice_id": choice_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        state.current_node_id = choice_id
        if choice_id not in state.visited_nodes:
            state.visited_nodes.append(choice_id)

        next_node = self._get_node(choice_id)
        self._apply_effects(state, next_node.get("effects", {}))
        self.save_session(session_id)
        return self._node_to_narration(next_node)

    def save_session(self, session_id: str):
        state = self._sessions.get(session_id)
        if state is None:
            return
        session_file = self._sessions_dir / f"{session_id}.json"
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(state.model_dump(), f, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed to save session %s: %s", session_id, exc)

    def load_session(self, session_id: str) -> Optional[StoryState]:
        session_file = self._sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = StoryState(**data)
            self._sessions[session_id] = state
            return state
        except Exception as exc:
            logger.error("Failed to load session %s: %s", session_id, exc)
            return None

    def reset_session(self, session_id: str):
        start_node = self._story_data.get("start_node", "start")
        state = StoryState(session_id=session_id, current_node_id=start_node)
        state.visited_nodes.append(start_node)
        self._sessions[session_id] = state
        self.save_session(session_id)

    def delete_session(self, session_id: str):
        """Remove a session from memory and disk."""
        self._sessions.pop(session_id, None)
        session_file = self._sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()


        sessions = []
        for f in self._sessions_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                sessions.append({"session_id": f.stem, "current_node_id": data.get("current_node_id")})
            except Exception:
                pass
        return sessions
