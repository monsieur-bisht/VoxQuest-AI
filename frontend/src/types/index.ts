export interface StoryChoice {
  choice_id: string;
  text: string;
  consequence_preview?: string;
}

export interface StoryNarration {
  narration_text: string;
  choices: StoryChoice[];
  node_id: string;
  emotional_tone: string;
  is_ending: boolean;
}

export interface StoryState {
  session_id: string;
  current_node_id: string;
  character_name: string;
  health: number;
  relationship_score: number;
  inventory: string[];
  visited_nodes: string[];
  story_log: Array<{ node_id: string; choice_made?: string; timestamp: string }>;
}

export interface TranscriptionResult {
  session_id: string;
  transcript: string;
  confidence: number;
  language: string;
  wer?: number;
  processing_time_ms: number;
  audio_duration_s: number;
}

export interface BenchmarkResult {
  run_id: string;
  model_name: string;
  avg_wer: number;
  avg_cer: number;
  avg_latency_ms: number;
  total_samples: number;
  passed: number;
  failed: number;
  results_by_language: Record<string, { wer: number; cer: number; count: number }>;
}

export interface MetricsData {
  total_sessions: number;
  avg_wer: number;
  avg_latency_ms: number;
  top_languages: string[];
  recent_sessions: string[];
}

export type RecordingState = 'idle' | 'recording' | 'processing' | 'done' | 'error';
export type EmotionalTone =
  | 'neutral'
  | 'tense'
  | 'joyful'
  | 'mysterious'
  | 'dramatic'
  | 'peaceful';
