"""Tests for StoryService: session creation, narration, choices, persistence."""
import sys
import os
import uuid
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.story_service import StoryService


@pytest.fixture
def story_service(tmp_path):
    """Return a StoryService using a temp directory (no real story file needed)."""
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return StoryService(stories_dir=str(stories_dir), data_dir=str(data_dir))


@pytest.fixture
def new_session_id():
    return str(uuid.uuid4())


class TestSessionCreation:
    def test_creates_new_session(self, story_service, new_session_id):
        state = story_service.get_or_create_session(new_session_id)
        assert state is not None
        assert state.session_id == new_session_id

    def test_session_starts_at_start_node(self, story_service, new_session_id):
        state = story_service.get_or_create_session(new_session_id)
        assert state.current_node_id == "start"

    def test_session_persists_on_second_call(self, story_service, new_session_id):
        state1 = story_service.get_or_create_session(new_session_id)
        state2 = story_service.get_or_create_session(new_session_id)
        assert state1.session_id == state2.session_id

    def test_visited_nodes_contains_start(self, story_service, new_session_id):
        state = story_service.get_or_create_session(new_session_id)
        assert "start" in state.visited_nodes


class TestNarration:
    def test_get_initial_narration_returns_narration(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        assert narration is not None
        assert isinstance(narration.narration_text, str)
        assert len(narration.narration_text) > 0

    def test_initial_narration_has_choices(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        assert isinstance(narration.choices, list)
        assert len(narration.choices) > 0

    def test_narration_has_node_id(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        assert narration.node_id is not None

    def test_narration_has_emotional_tone(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        assert narration.emotional_tone is not None


class TestChoices:
    def test_valid_choice_advances_story(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        choice_id = narration.choices[0].choice_id
        next_narration = story_service.process_choice(new_session_id, choice_id)
        assert next_narration is not None
        assert isinstance(next_narration.narration_text, str)

    def test_choice_changes_current_node(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        choice_id = narration.choices[0].choice_id
        story_service.process_choice(new_session_id, choice_id)
        state = story_service.get_or_create_session(new_session_id)
        assert state.current_node_id == choice_id

    def test_invalid_choice_raises_error(self, story_service, new_session_id):
        from fastapi import HTTPException
        story_service.get_or_create_session(new_session_id)
        with pytest.raises(HTTPException):
            story_service.process_choice(new_session_id, "nonexistent_choice_xyz")

    def test_choice_logged_in_story_log(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        choice_id = narration.choices[0].choice_id
        story_service.process_choice(new_session_id, choice_id)
        state = story_service.get_or_create_session(new_session_id)
        assert len(state.story_log) > 0


class TestPersistence:
    def test_save_and_reload_session(self, story_service, new_session_id, tmp_path):
        story_service.get_or_create_session(new_session_id)
        story_service.save_session(new_session_id)

        # Clear in-memory cache and reload
        story_service._sessions.clear()
        loaded = story_service.load_session(new_session_id)
        assert loaded is not None
        assert loaded.session_id == new_session_id

    def test_load_nonexistent_session_returns_none(self, story_service):
        result = story_service.load_session("nonexistent-session-id-xyz")
        assert result is None


class TestReset:
    def test_reset_returns_to_start(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        choice_id = narration.choices[0].choice_id
        story_service.process_choice(new_session_id, choice_id)

        story_service.reset_session(new_session_id)
        state = story_service.get_or_create_session(new_session_id)
        assert state.current_node_id == "start"

    def test_reset_clears_story_log(self, story_service, new_session_id):
        narration = story_service.get_current_narration(new_session_id)
        story_service.process_choice(new_session_id, narration.choices[0].choice_id)
        story_service.reset_session(new_session_id)
        state = story_service.get_or_create_session(new_session_id)
        assert state.story_log == []
