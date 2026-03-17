"""Text utility functions: language detection, Hinglish normalisation, ASR post-processing."""

from __future__ import annotations

import re
import unicodedata
from typing import List


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# Unicode block ranges
_DEVANAGARI_RANGE = range(0x0900, 0x097F + 1)


def _has_devanagari(text: str) -> bool:
    return any(ord(ch) in _DEVANAGARI_RANGE for ch in text)


def _has_latin(text: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in text)


def detect_language(text: str) -> str:
    """Detect whether *text* is English, Hindi, or code-switched Hindi-English.

    Uses a simple heuristic based on Unicode script analysis rather than a
    statistical model, so it works offline with no dependencies.

    Returns
    -------
    str
        One of ``"en"``, ``"hi"``, or ``"hi-en"``.
    """
    if not text.strip():
        return "en"

    has_dev = _has_devanagari(text)
    has_lat = _has_latin(text)

    if has_dev and has_lat:
        return "hi-en"
    if has_dev:
        return "hi"
    return "en"


# ---------------------------------------------------------------------------
# Hinglish normalisation
# ---------------------------------------------------------------------------

# Common Hinglish romanisation variants → canonical form.
_HINGLISH_NORMALISE: dict[str, str] = {
    r"\bkya\b": "kya",
    r"\bkyaa\b": "kya",
    r"\bhai\b": "hai",
    r"\bhain\b": "hain",
    r"\bnahi\b": "nahi",
    r"\bnahin\b": "nahi",
    r"\bnah\b": "nahi",
    r"\baur\b": "aur",
    r"\baour\b": "aur",
    r"\bmein\b": "mein",
    r"\bmain\b": "mein",
    r"\bme\b": "mein",
    r"\bjungle\b": "jungle",
    r"\bjangal\b": "jungle",
    r"\bkaro\b": "karo",
    r"\bkaroo\b": "karo",
    r"\btheek\b": "theek",
    r"\bthik\b": "theek",
    r"\btik\b": "theek",
    r"\bacha\b": "acha",
    r"\bachha\b": "acha",
}


def transliterate_hinglish(text: str) -> str:
    """Normalise common Hinglish romanisation variants to a canonical form.

    This is a best-effort normalisation; it does not perform full
    transliteration between scripts.

    Parameters
    ----------
    text:
        Input string (Latin-script Hinglish or mixed).

    Returns
    -------
    str
        Text with common variant spellings collapsed to canonical forms.
    """
    normalised = text.lower()
    for pattern, replacement in _HINGLISH_NORMALISE.items():
        normalised = re.sub(pattern, replacement, normalised, flags=re.IGNORECASE)
    return normalised


# ---------------------------------------------------------------------------
# Choice extraction
# ---------------------------------------------------------------------------

_CHOICE_PATTERNS = [
    # "1. Choice text" or "1) Choice text"
    re.compile(r"^\s*(\d+)[.)]\s*(.+)$", re.MULTILINE),
    # "A. Choice text" or "A) Choice text"
    re.compile(r"^\s*([A-Za-z])[.)]\s*(.+)$", re.MULTILINE),
    # "• Choice text" or "- Choice text" or "* Choice text"
    re.compile(r"^\s*[•\-\*]\s*(.+)$", re.MULTILINE),
]


def extract_choices_from_text(text: str) -> List[str]:
    """Extract numbered or bulleted choices from narration *text*.

    Looks for patterns like:
    * ``1. Enter the jungle``
    * ``A) Wait for dawn``
    * ``• Follow the water``
    * ``- Investigate the smoke``

    Returns
    -------
    list[str]
        Extracted choice strings (stripped); empty list when none found.
    """
    choices: List[str] = []
    for pattern in _CHOICE_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            for match in matches:
                # match may be a tuple (label, text) or a single string
                if isinstance(match, tuple):
                    choices.append(match[-1].strip())
                else:
                    choices.append(match.strip())
            if choices:
                return choices
    return choices


# ---------------------------------------------------------------------------
# ASR output cleaning
# ---------------------------------------------------------------------------

# Patterns commonly produced by ASR engines that should be stripped.
_ASR_ARTEFACTS = [
    re.compile(r"\[.*?\]"),          # [BLANK], [inaudible], etc.
    re.compile(r"\(.*?\)"),          # (laughs), (noise), etc.
    re.compile(r"<[^>]+>"),          # <unk>, <sil>, XML/HTML tags
    re.compile(r"\buh+\b", re.I),    # "uh", "uhh"
    re.compile(r"\bum+\b", re.I),    # "um", "umm"
    re.compile(r"\bhmm+\b", re.I),   # "hmm"
    re.compile(r"\beh+\b", re.I),    # "eh"
    re.compile(r"\.{2,}"),           # ellipsis "..."
]


def clean_asr_output(text: str) -> str:
    """Remove common ASR artefacts from *text*.

    Strips filler tokens (``[BLANK]``, ``<unk>``), hesitation markers
    (``uh``, ``um``), repeated punctuation, and excess whitespace.

    Parameters
    ----------
    text:
        Raw ASR transcript string.

    Returns
    -------
    str
        Cleaned transcript.
    """
    cleaned = text
    for pattern in _ASR_ARTEFACTS:
        cleaned = pattern.sub(" ", cleaned)

    # Collapse multiple spaces / newlines and strip.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove leading/trailing punctuation artefacts.
    cleaned = cleaned.strip(".,;:!?-–— ")

    return cleaned
