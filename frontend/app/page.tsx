"use client";

import { useMemo, useState } from "react";

import { VoiceRecorder } from "@/components/VoiceRecorder";

type StartResponse = {
  session_id: string;
  scene_id: string;
  narration: string;
  choices: string[];
  relationship_score: number;
  emotion: string;
  tts: { rate: number; pitch: number };
};

type TurnResponse = {
  scene_id: string;
  narration: string;
  choices: string[];
  relationship_score: number;
  emotion: string;
  tts: { rate: number; pitch: number };
  benchmark: { wer: number | null; confidence: number; latency_ms: number; language_mode: string };
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function HomePage() {
  const [session, setSession] = useState<StartResponse | null>(null);
  const [transcript, setTranscript] = useState("");
  const [narration, setNarration] = useState("Start a session to begin your voice RPG quest.");
  const [choices, setChoices] = useState<string[]>([]);
  const [relationship, setRelationship] = useState(0);
  const [benchmark, setBenchmark] = useState<TurnResponse["benchmark"] | null>(null);
  const [datasetStatus, setDatasetStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const canPlay = useMemo(() => !!session?.session_id && transcript.trim().length > 0, [session, transcript]);

  const speak = (text: string, rate = 1, pitch = 1) => {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = rate;
    utterance.pitch = pitch;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const startGame = async () => {
    setLoading(true);
    const response = await fetch(`${apiBase}/api/game/start`, { method: "POST" });
    const data: StartResponse = await response.json();
    setSession(data);
    setNarration(data.narration);
    setChoices(data.choices);
    setRelationship(data.relationship_score);
    speak(data.narration, data.tts.rate, data.tts.pitch);
    setLoading(false);
  };

  const sendTurn = async (text?: string) => {
    if (!session) return;
    setLoading(true);
    const usedTranscript = (text ?? transcript).trim();
    const response = await fetch(`${apiBase}/api/game/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: session.session_id,
        transcript: usedTranscript,
        expected_transcript: usedTranscript,
        confidence: 0.9,
        noise_level: "medium",
        accent_tag: "neutral",
      }),
    });
    const data: TurnResponse = await response.json();
    setNarration(data.narration);
    setChoices(data.choices);
    setRelationship(data.relationship_score);
    setBenchmark(data.benchmark);
    speak(data.narration, data.tts.rate, data.tts.pitch);
    setLoading(false);
  };

  const transcribeAudio = async (blob: Blob) => {
    if (!session) return;
    const form = new FormData();
    form.append("audio", blob, "voice.webm");
    form.append("session_id", session.session_id);
    form.append("language_hint", "auto");
    form.append("noise_level", "medium");
    form.append("accent_tag", "neutral");

    const response = await fetch(`${apiBase}/api/speech/transcribe`, {
      method: "POST",
      body: form,
    });

    const data = await response.json();
    setTranscript(data.transcript);
  };

  const tagSample = async () => {
    if (!session || !transcript.trim()) return;
    const language = benchmark?.language_mode ?? "english";
    await fetch(`${apiBase}/api/dataset/tag`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: session.session_id,
        transcript,
        language_tag: language,
        noise_level: "medium",
        accent_tag: "neutral",
        anonymized_audio_id: `${session.session_id.slice(0, 8)}-${Date.now()}`,
      }),
    });
    setDatasetStatus("Latest transcript tagged for dataset export.");
  };

  const saveSession = async () => {
    if (!session) return;
    await fetch(`${apiBase}/api/game/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: session.session_id }),
    });
  };

  const loadSession = async () => {
    if (!session) return;
    const response = await fetch(`${apiBase}/api/game/load`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: session.session_id }),
    });
    const data = await response.json();
    setNarration(data.narration);
    setChoices(data.choices);
    setRelationship(data.relationship_score);
  };

  return (
    <main className="container">
      <h1>VoxQuest-AI</h1>
      <p className="subtitle">Voice-first Interactive RPG + Speech AI Benchmarking Starter</p>

      <div className="panel-row">
        <button className="action-btn" onClick={startGame} disabled={loading}>
          {session ? "Restart Adventure" : "Start Adventure"}
        </button>
        <button className="action-btn" onClick={saveSession} disabled={!session || loading}>
          Save
        </button>
        <button className="action-btn" onClick={loadSession} disabled={!session || loading}>
          Load
        </button>
      </div>

      <VoiceRecorder onRecorded={transcribeAudio} />

      <textarea
        className="transcript-box"
        placeholder="Transcript appears here or type your choice..."
        value={transcript}
        onChange={(event) => setTranscript(event.target.value)}
      />

      <button className="action-btn" disabled={!canPlay || loading} onClick={() => sendTurn()}>
        Send Voice Turn
      </button>

      <section className="story-panel">
        <h2>Narration</h2>
        <p>{narration}</p>
      </section>

      <section className="choices-panel">
        {choices.map((choice) => (
          <button key={choice} className="choice-btn" onClick={() => sendTurn(choice)} disabled={loading}>
            {choice}
          </button>
        ))}
      </section>

      <section className="stats-panel">
        <div>Relationship: {relationship}</div>
        <div>WER: {benchmark?.wer ?? "n/a"}</div>
        <div>Confidence: {benchmark?.confidence ?? "n/a"}</div>
        <div>Latency: {benchmark?.latency_ms ?? "n/a"} ms</div>
        <div>Language: {benchmark?.language_mode ?? "n/a"}</div>
      </section>

      <section className="panel-row">
        <button className="action-btn" onClick={tagSample} disabled={!session || !transcript.trim() || loading}>
          Tag Current Transcript
        </button>
        <a className="action-btn" href={`${apiBase}/api/dataset/export?format=json`} target="_blank" rel="noreferrer">
          Export JSON
        </a>
        <a className="action-btn" href={`${apiBase}/api/dataset/export?format=csv`} target="_blank" rel="noreferrer">
          Export CSV
        </a>
      </section>
      {datasetStatus ? <p className="subtitle">{datasetStatus}</p> : null}
    </main>
  );
}
