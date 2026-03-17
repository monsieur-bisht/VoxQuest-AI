from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class AudioTranscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: str = "en"
    expected_text: Optional[str] = None


class AudioTranscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: str
    wer: Optional[float] = None
    processing_time_ms: float
    audio_duration_s: float


class TTSRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1, max_length=5000)
    voice_id: Optional[str] = None
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0)
    language: Optional[str] = "en"


class TTSResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    audio_url: str
    duration_s: float
    engine_used: str


class StoryState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    current_node_id: str = "start"
    character_name: str = "Adventurer"
    health: int = Field(default=100, ge=0, le=100)
    relationship_score: int = Field(default=50, ge=0, le=100)
    inventory: List[str] = Field(default_factory=list)
    visited_nodes: List[str] = Field(default_factory=list)
    story_log: List[Dict[str, Any]] = Field(default_factory=list)


class StoryChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choice_id: str
    text: str
    consequence_preview: Optional[str] = None


class StoryNarration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    narration_text: str
    choices: List[StoryChoice] = Field(default_factory=list)
    node_id: str
    emotional_tone: str = "neutral"
    is_ending: bool = False


class BenchmarkRun(BaseModel):
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    run_id: str
    model_name: str
    avg_wer: float
    avg_cer: float
    avg_latency_ms: float
    total_samples: int
    passed: int
    failed: int
    results_by_language: Dict[str, Any] = Field(default_factory=dict)


class SessionInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    story_state: Optional[StoryState] = None


class DatasetEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    audio_path: str
    transcript: str
    expected_text: Optional[str] = None
    wer: Optional[float] = None
    language: str = "en"
    accent_tag: Optional[str] = None
    noise_level: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_sessions: int
    avg_wer: float
    avg_latency_ms: float
    top_languages: List[Dict[str, Any]]
    recent_sessions: List[Dict[str, Any]]
