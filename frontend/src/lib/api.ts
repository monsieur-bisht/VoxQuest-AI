import type {
  StoryNarration,
  StoryState,
  TranscriptionResult,
  BenchmarkResult,
  MetricsData,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`API error ${response.status}: ${errorText}`);
  }
  return response.json() as Promise<T>;
}

export async function startStorySession(
  sessionId: string,
  characterName: string
): Promise<StoryNarration> {
  return fetchJSON<StoryNarration>(`${API_BASE}/api/story/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, character_name: characterName }),
  });
}

export async function makeChoice(
  sessionId: string,
  choiceId: string
): Promise<StoryNarration> {
  return fetchJSON<StoryNarration>(`${API_BASE}/api/story/choice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, choice_id: choiceId }),
  });
}

export async function getStoryState(sessionId: string): Promise<StoryState> {
  return fetchJSON<StoryState>(`${API_BASE}/api/story/state/${sessionId}`);
}

export async function resetSession(sessionId: string): Promise<void> {
  await fetchJSON<unknown>(`${API_BASE}/api/story/reset/${sessionId}`, {
    method: 'POST',
  });
}

export async function transcribeAudio(
  audioBlob: Blob,
  sessionId: string,
  language = 'en'
): Promise<TranscriptionResult> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');
  formData.append('session_id', sessionId);
  formData.append('language', language);

  return fetchJSON<TranscriptionResult>(`${API_BASE}/api/transcribe`, {
    method: 'POST',
    body: formData,
  });
}

export async function synthesizeSpeech(text: string, language = 'en'): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  if (!response.ok) {
    throw new Error(`TTS error ${response.status}`);
  }
  return response.blob();
}

export async function getBenchmarkMetrics(): Promise<MetricsData> {
  return fetchJSON<MetricsData>(`${API_BASE}/api/benchmark/metrics`);
}

export async function getBenchmarkResults(): Promise<BenchmarkResult[]> {
  return fetchJSON<BenchmarkResult[]>(`${API_BASE}/api/benchmark/results`);
}

export async function runBenchmark(modelName: string): Promise<BenchmarkResult> {
  return fetchJSON<BenchmarkResult>(`${API_BASE}/api/benchmark/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_name: modelName }),
  });
}
