"""Facebook Wav2Vec2 ASR implementation via HuggingFace Transformers."""

import io
import logging
import time

from ml.asr.base_asr import ASRResult, BaseASR

logger = logging.getLogger(__name__)


class Wav2Vec2ASR(BaseASR):
    """ASR backend powered by Facebook's Wav2Vec2 via HuggingFace Transformers.

    Parameters
    ----------
    model_id:
        HuggingFace model identifier, e.g. ``"facebook/wav2vec2-base-960h"``
        or ``"facebook/wav2vec2-large-960h-lv60-self"``.
    """

    model_name = "wav2vec2"
    supported_languages = ["en"]

    def __init__(self, model_id: str = "facebook/wav2vec2-base-960h") -> None:
        self.model_id = model_id
        self._model = None
        self._processor = None

    # ------------------------------------------------------------------
    # BaseASR interface
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Download and cache the Wav2Vec2 processor + model weights."""
        if self._model is not None:
            return
        try:
            from transformers import (  # type: ignore
                Wav2Vec2ForCTC,
                Wav2Vec2Processor,
            )

            logger.info("Loading Wav2Vec2 model '%s'…", self.model_id)
            self._processor = Wav2Vec2Processor.from_pretrained(self.model_id)
            self._model = Wav2Vec2ForCTC.from_pretrained(self.model_id)
            self._model.eval()
            logger.info("Wav2Vec2 model '%s' loaded.", self.model_id)
        except ImportError:
            logger.warning(
                "transformers / torch not installed; Wav2Vec2ASR will run in stub mode."
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to load Wav2Vec2 model: %s", exc)

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> ASRResult:
        """Transcribe *audio_bytes* with Wav2Vec2.

        Falls back to a stub when transformers or torch is unavailable.
        """
        start_ms = time.monotonic() * 1000

        if self._model is None:
            self.load_model()

        if self._model is None:
            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript="[wav2vec2 unavailable – stub transcript]",
                confidence=0.0,
                language=language,
                processing_time_ms=round(elapsed, 2),
            )

        try:
            import numpy as np  # type: ignore
            import torch  # type: ignore
            from ml.utils.audio_utils import bytes_to_numpy

            # Decode the audio bytes → 16 kHz mono float32 numpy array.
            audio_array = bytes_to_numpy(audio_bytes, sample_rate=16000)

            inputs = self._processor(
                audio_array,
                sampling_rate=16000,
                return_tensors="pt",
                padding=True,
            )

            with torch.no_grad():
                logits = self._model(**inputs).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            transcript: str = self._processor.batch_decode(predicted_ids)[0].strip()

            # Wav2Vec2 doesn't expose per-token confidence; use a simple heuristic.
            probs = torch.softmax(logits, dim=-1)
            token_conf = probs.max(dim=-1).values.mean().item()
            confidence = float(max(0.0, min(1.0, token_conf)))

            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript=transcript,
                confidence=confidence,
                language=language,
                processing_time_ms=round(elapsed, 2),
            )

        except Exception as exc:  # pragma: no cover
            logger.error("Wav2Vec2 transcription error: %s", exc)
            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript="",
                confidence=0.0,
                language=language,
                processing_time_ms=round(elapsed, 2),
            )
