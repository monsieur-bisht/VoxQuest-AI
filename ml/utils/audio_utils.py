"""Audio utility functions: numpy ↔ bytes conversion, noise, resampling."""

from __future__ import annotations

import io
import struct
import wave
from typing import List


def bytes_to_numpy(audio_bytes: bytes, sample_rate: int = 16000):
    """Convert raw audio bytes to a float32 NumPy array.

    Supports:
    * **WAV** bytes (detected by ``RIFF`` header).
    * **Raw 16-bit PCM** bytes (assumed when no WAV header is present).

    Parameters
    ----------
    audio_bytes:
        Audio data.
    sample_rate:
        Target sample rate (used only for raw PCM; WAV files carry their own).

    Returns
    -------
    numpy.ndarray
        Mono float32 array normalised to ``[-1.0, 1.0]``.
    """
    import numpy as np  # type: ignore

    if audio_bytes[:4] == b"RIFF":
        # WAV bytes
        with io.BytesIO(audio_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())
        dtype = np.int16 if sampwidth == 2 else np.int32
        audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)
        audio /= np.iinfo(dtype).max
        return audio

    # Assume raw 16-bit PCM
    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    audio /= 32768.0
    return audio


def numpy_to_bytes(audio_array, sample_rate: int = 16000) -> bytes:
    """Convert a float32 NumPy array to 16-bit mono WAV bytes.

    Parameters
    ----------
    audio_array:
        Float32 array with values in ``[-1.0, 1.0]``.
    sample_rate:
        Sample rate in Hz.

    Returns
    -------
    bytes
        Valid WAV byte string.
    """
    import numpy as np  # type: ignore

    audio = np.clip(audio_array, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def add_noise(audio, snr_db: float = 10.0):
    """Add Gaussian white noise to *audio* at the specified SNR.

    Parameters
    ----------
    audio:
        Float32 NumPy array.
    snr_db:
        Desired signal-to-noise ratio in decibels.

    Returns
    -------
    numpy.ndarray
        Noisy audio array, same shape as *audio*.
    """
    import numpy as np  # type: ignore

    signal_power = np.mean(audio ** 2)
    if signal_power == 0:
        return audio.copy()
    snr_linear = 10 ** (snr_db / 10.0)
    noise_power = signal_power / snr_linear
    noise = np.random.normal(0, np.sqrt(noise_power), audio.shape).astype(np.float32)
    return audio + noise


def resample_audio(audio, orig_sr: int, target_sr: int):
    """Resample *audio* from *orig_sr* to *target_sr*.

    Uses ``librosa.resample`` when available, falling back to linear
    interpolation via ``numpy``.

    Parameters
    ----------
    audio:
        Float32 NumPy array.
    orig_sr:
        Original sample rate in Hz.
    target_sr:
        Desired sample rate in Hz.

    Returns
    -------
    numpy.ndarray
        Resampled audio array.
    """
    import numpy as np  # type: ignore

    if orig_sr == target_sr:
        return audio.copy()

    try:
        import librosa  # type: ignore

        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    except ImportError:
        pass

    # Linear interpolation fallback.
    n_orig = len(audio)
    n_target = int(n_orig * target_sr / orig_sr)
    x_orig = np.linspace(0, 1, n_orig)
    x_new = np.linspace(0, 1, n_target)
    return np.interp(x_new, x_orig, audio).astype(np.float32)


def get_audio_duration(audio_bytes: bytes) -> float:
    """Return the duration of an audio byte string in seconds.

    Supports WAV.  Falls back to a heuristic for unknown formats.

    Parameters
    ----------
    audio_bytes:
        Raw audio bytes.

    Returns
    -------
    float
        Duration in seconds.
    """
    if audio_bytes[:4] == b"RIFF":
        try:
            with io.BytesIO(audio_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    return wf.getnframes() / wf.getframerate()
        except Exception:
            pass
    # Heuristic: assume 16-bit mono 16 kHz PCM.
    return max(0.0, len(audio_bytes) / 32000.0)


def split_audio(audio, chunk_size_s: float = 30.0, sample_rate: int = 16000) -> List:
    """Split *audio* into non-overlapping chunks of at most *chunk_size_s* seconds.

    Parameters
    ----------
    audio:
        Float32 NumPy array.
    chunk_size_s:
        Maximum length of each chunk in seconds.
    sample_rate:
        Sample rate of *audio*.

    Returns
    -------
    list[numpy.ndarray]
        List of audio chunks.  The final chunk may be shorter than
        *chunk_size_s*.
    """
    import numpy as np  # type: ignore

    chunk_len = int(chunk_size_s * sample_rate)
    if chunk_len <= 0:
        raise ValueError("chunk_size_s must be positive.")
    n = len(audio)
    return [audio[i : i + chunk_len] for i in range(0, n, chunk_len)]
