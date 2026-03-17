import logging
from typing import Any, Dict, Optional

from app.models.schemas import StoryState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a dramatic narrator for a text-based RPG called VoxQuest. "
    "Respond as an immersive fantasy narrator. Keep responses under 150 words. "
    "End with exactly the choices the player has available, listed as short phrases."
)

_FALLBACK_RESPONSES = [
    "The ancient forest whispers around you. Strange runes glow on a mossy stone ahead.",
    "A fork in the path appears. The left trail leads deeper into shadow; the right toward distant firelight.",
    "The village elder regards you carefully, measuring your worth with wise, tired eyes.",
    "A mysterious figure steps from the shadows, hand resting on the hilt of a blade.",
    "The dungeon stretches before you, cold air carrying the scent of old magic and danger.",
]


class LLMService:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-3.5-turbo",
        api_key: str = "",
    ):
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._fallback_index = 0

    def _next_fallback(self) -> str:
        msg = _FALLBACK_RESPONSES[self._fallback_index % len(_FALLBACK_RESPONSES)]
        self._fallback_index += 1
        return msg

    def build_story_prompt(
        self, story_state: StoryState, player_input: str, story_node: Dict[str, Any]
    ) -> str:
        node_text = story_node.get("narration", "")
        choices_text = "\n".join(
            f"- {c.get('choice_id', '')}: {c.get('text', '')}"
            for c in story_node.get("choices", [])
        )
        prompt = (
            f"Character: {story_state.character_name}\n"
            f"Health: {story_state.health}/100\n"
            f"Relationship score: {story_state.relationship_score}/100\n"
            f"Inventory: {', '.join(story_state.inventory) or 'empty'}\n\n"
            f"Current scene:\n{node_text}\n\n"
            f"Available choices:\n{choices_text}\n\n"
            f"Player said: \"{player_input}\"\n\n"
            "Continue the narration naturally, then list the choices again."
        )
        return prompt

    async def generate_story_response(
        self,
        prompt: str,
        context: Dict[str, Any],
        system_prompt: str = _SYSTEM_PROMPT,
    ) -> str:
        if not self._api_key:
            return self._next_fallback()

        if self._provider == "openai":
            return await self._call_openai(prompt, system_prompt)
        if self._provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt)
        return self._next_fallback()

    async def _call_openai(self, prompt: str, system_prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._api_key)
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.8,
            )
            return response.choices[0].message.content or self._next_fallback()
        except Exception as exc:
            logger.warning("OpenAI call failed: %s", exc)
            return self._next_fallback()

    async def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self._api_key)
            message = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text if message.content else self._next_fallback()
        except Exception as exc:
            logger.warning("Anthropic call failed: %s", exc)
            return self._next_fallback()
