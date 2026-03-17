"""ASR model registry: maps short names to configured model instances."""

from __future__ import annotations

import logging
from typing import Callable

from ml.asr.base_asr import BaseASR

logger = logging.getLogger(__name__)

# Registry is built lazily so that heavy imports happen only when a model is
# actually requested.  Each value is a zero-argument factory that returns a
# pre-configured BaseASR instance.
_ASR_FACTORIES: dict[str, Callable[[], BaseASR]] = {}


def _register_defaults() -> None:
    """Populate _ASR_FACTORIES with the built-in model definitions."""
    from ml.asr.whisper_model import WhisperASR
    from ml.asr.wav2vec2_model import Wav2Vec2ASR

    _ASR_FACTORIES.update(
        {
            "whisper-tiny": lambda: WhisperASR(model_size="tiny"),
            "whisper-base": lambda: WhisperASR(model_size="base"),
            "whisper-small": lambda: WhisperASR(model_size="small"),
            "whisper-medium": lambda: WhisperASR(model_size="medium"),
            "whisper-large": lambda: WhisperASR(model_size="large"),
            "wav2vec2-base": lambda: Wav2Vec2ASR(
                model_id="facebook/wav2vec2-base-960h"
            ),
            "wav2vec2-large": lambda: Wav2Vec2ASR(
                model_id="facebook/wav2vec2-large-960h-lv60-self"
            ),
        }
    )


_register_defaults()

# Public alias – read-only view of available model names.
ASR_REGISTRY: dict[str, Callable[[], BaseASR]] = _ASR_FACTORIES


def get_asr_model(model_name: str) -> BaseASR:
    """Return a new, configured :class:`BaseASR` instance for *model_name*.

    Parameters
    ----------
    model_name:
        One of the keys in :data:`ASR_REGISTRY` (e.g. ``"whisper-base"``).

    Raises
    ------
    KeyError
        If *model_name* is not found in the registry.
    """
    if model_name not in _ASR_FACTORIES:
        available = ", ".join(sorted(_ASR_FACTORIES))
        raise KeyError(
            f"Unknown ASR model '{model_name}'. Available models: {available}"
        )
    logger.debug("Creating ASR model '%s'.", model_name)
    return _ASR_FACTORIES[model_name]()
