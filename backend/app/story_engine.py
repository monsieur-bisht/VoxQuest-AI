from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Scene:
    scene_id: str
    narration: str
    choices: Dict[str, str]
    emotion: str = "neutral"
    relationship_delta: int = 0


SCENES: Dict[str, Scene] = {
    "start": Scene(
        scene_id="start",
        narration="A wizardly tower glows in the distance while your companion Mira watches for your next move.",
        choices={
            "Investigate the tower": "tower_gate",
            "Take the forest path": "forest_path",
            "Return to village": "village_return",
        },
        emotion="mysterious",
    ),
    "tower_gate": Scene(
        scene_id="tower_gate",
        narration="At the obsidian gate, Mira smiles at your courage. Strange runes hum as if recognizing your voice.",
        choices={
            "Speak to the runes in Hindi-English": "rune_trial",
            "Ask Mira to lead": "mira_leads",
        },
        emotion="tense",
        relationship_delta=2,
    ),
    "forest_path": Scene(
        scene_id="forest_path",
        narration="The forest whispers in two tongues; you hear 'ruk jao' and 'move now' at once as shadows shift.",
        choices={
            "Follow the Hindi whisper": "river_crossing",
            "Follow the English whisper": "rune_trial",
        },
        emotion="eerie",
    ),
    "village_return": Scene(
        scene_id="village_return",
        narration="The village elder warns that waiting too long will seal the tower forever.",
        choices={
            "Head back to the tower": "tower_gate",
            "Gather supplies first": "river_crossing",
        },
        emotion="serious",
    ),
    "rune_trial": Scene(
        scene_id="rune_trial",
        narration="Your mixed-language chant unlocks the archway. Mira calls you brilliant as the gateway opens.",
        choices={
            "Enter the tower": "ending_victory",
            "Set up camp": "ending_camp",
        },
        emotion="triumphant",
        relationship_delta=3,
    ),
    "mira_leads": Scene(
        scene_id="mira_leads",
        narration="Mira steps forward but the gate rejects her. She seems hurt by your hesitation.",
        choices={
            "Apologize and step in": "rune_trial",
            "Retreat to village": "village_return",
        },
        emotion="melancholic",
        relationship_delta=-1,
    ),
    "river_crossing": Scene(
        scene_id="river_crossing",
        narration="A flooded bridge roars ahead; static-like wind makes speech recognition difficult.",
        choices={
            "Shout directions": "ending_camp",
            "Wait for calm weather": "tower_gate",
        },
        emotion="urgent",
    ),
    "ending_victory": Scene(
        scene_id="ending_victory",
        narration="Inside the tower, your voice binds an ancient pact. Quest complete.",
        choices={},
        emotion="joyful",
    ),
    "ending_camp": Scene(
        scene_id="ending_camp",
        narration="You make camp under neon stars, promising to continue at dawn.",
        choices={},
        emotion="calm",
    ),
}


def get_scene(scene_id: str) -> Scene:
    return SCENES.get(scene_id, SCENES["start"])


def advance_scene(current_scene_id: str, user_input: str) -> Scene:
    scene = get_scene(current_scene_id)
    lower = user_input.lower()

    for choice, next_scene_id in scene.choices.items():
        words = choice.lower().split()
        if any(word in lower for word in words):
            return get_scene(next_scene_id)

    if scene.choices:
        first_next = next(iter(scene.choices.values()))
        return get_scene(first_next)

    return scene


def detect_language_mode(text: str) -> str:
    hindi_markers = {"hai", "kya", "nahi", "ruk", "jao", "chalo"}
    english_markers = {"go", "tower", "forest", "village", "camp"}
    text_words = set(text.lower().replace("-", " ").split())

    has_hi = any(word in text_words for word in hindi_markers)
    has_en = any(word in text_words for word in english_markers)

    if has_hi and has_en:
        return "hinglish"
    if has_hi:
        return "hindi"
    return "english"


def tone_modifier(emotion: str) -> Dict[str, float]:
    modifiers = {
        "mysterious": {"rate": 0.92, "pitch": 1.05},
        "tense": {"rate": 1.02, "pitch": 0.95},
        "eerie": {"rate": 0.9, "pitch": 0.85},
        "serious": {"rate": 0.94, "pitch": 0.9},
        "triumphant": {"rate": 1.04, "pitch": 1.1},
        "melancholic": {"rate": 0.88, "pitch": 0.85},
        "urgent": {"rate": 1.1, "pitch": 1.0},
        "joyful": {"rate": 1.05, "pitch": 1.15},
        "calm": {"rate": 0.9, "pitch": 1.0},
    }
    return modifiers.get(emotion, {"rate": 1.0, "pitch": 1.0})


def list_choices(scene_id: str) -> List[str]:
    return list(get_scene(scene_id).choices.keys())
