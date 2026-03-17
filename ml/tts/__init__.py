"""TTS sub-package: gTTS and pyttsx3 model implementations."""

from ml.tts.base_tts import BaseTTS, TTSResult
from ml.tts.gtts_model import GTTSModel
from ml.tts.pyttsx3_model import PyTTSX3Model

__all__ = ["BaseTTS", "TTSResult", "GTTSModel", "PyTTSX3Model"]
