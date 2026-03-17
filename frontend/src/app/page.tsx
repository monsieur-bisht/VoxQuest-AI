'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Sword, RotateCcw, BarChart2, Loader2 } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

import VoiceRecorder from '@/components/VoiceRecorder';
import WaveformVisualizer from '@/components/WaveformVisualizer';
import StoryNarrator from '@/components/StoryNarrator';
import ChoiceButtons from '@/components/ChoiceButtons';
import SessionInfo from '@/components/SessionInfo';

import {
  startStorySession,
  makeChoice,
  getStoryState,
  resetSession,
  transcribeAudio,
} from '@/lib/api';
import type { StoryNarration, StoryState, TranscriptionResult } from '@/types';

// ─── Helpers ────────────────────────────────────────────────────────────────

function generateSessionId(): string {
  return `vq_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Try to match transcript to a choice by ordinal ("1", "one", "first") or
 * by checking if any word from the choice text appears in the transcript.
 */
function matchTranscriptToChoice(
  transcript: string,
  choices: StoryNarration['choices']
): string | null {
  const lower = transcript.toLowerCase().trim();
  const ordinals: Record<string, number> = {
    '1': 0, 'one': 0, 'first': 0,
    '2': 1, 'two': 1, 'second': 1,
    '3': 2, 'three': 2, 'third': 2,
    '4': 3, 'four': 3, 'fourth': 3,
  };

  for (const [word, idx] of Object.entries(ordinals)) {
    if (lower.includes(word) && idx < choices.length) {
      return choices[idx].choice_id;
    }
  }

  // Fuzzy: check if transcript contains any key words from choice text
  for (const choice of choices) {
    const words = choice.text.toLowerCase().split(/\s+/).filter((w) => w.length > 3);
    if (words.some((w) => lower.includes(w))) {
      return choice.choice_id;
    }
  }

  return null;
}

// ─── Screen types ────────────────────────────────────────────────────────────

type Screen = 'start' | 'game' | 'end';

// ─── Component ───────────────────────────────────────────────────────────────

export default function GamePage() {
  const [screen, setScreen] = useState<Screen>('start');
  const [characterName, setCharacterName] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [narration, setNarration] = useState<StoryNarration | null>(null);
  const [storyState, setStoryState] = useState<StoryState | null>(null);
  const [selectedChoice, setSelectedChoice] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState<TranscriptionResult | null>(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError] = useState<string | null>(null);

  const processingRef = useRef(false);

  // Load or create session ID from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('voxquest_session_id');
    setSessionId(stored ?? generateSessionId());
  }, []);

  // ─── Begin Quest ────────────────────────────────────────────────────────

  const handleBeginQuest = useCallback(async () => {
    if (!characterName.trim() || !sessionId) return;
    setError(null);
    setIsLoading(true);
    setStatusMsg('Summoning your adventure…');
    try {
      const narr = await startStorySession(sessionId, characterName.trim());
      localStorage.setItem('voxquest_session_id', sessionId);
      setNarration(narr);
      setScreen('game');
      setStatusMsg('');

      // Fetch initial state in background
      getStoryState(sessionId)
        .then(setStoryState)
        .catch(() => null);
    } catch (err) {
      setError('Could not connect to the server. Is the backend running?');
      setStatusMsg('');
    } finally {
      setIsLoading(false);
    }
  }, [characterName, sessionId]);

  // ─── Make Choice ────────────────────────────────────────────────────────

  const handleChoiceSelect = useCallback(
    async (choiceId: string) => {
      if (processingRef.current || !sessionId) return;
      processingRef.current = true;
      setSelectedChoice(choiceId);
      setError(null);
      setIsLoading(true);
      setStatusMsg('The story continues…');

      try {
        const narr = await makeChoice(sessionId, choiceId);
        setNarration(narr);
        setSelectedChoice(undefined);
        setTranscription(null);
        setStatusMsg('');

        if (narr.is_ending) {
          setScreen('end');
        }

        // Refresh state
        getStoryState(sessionId)
          .then(setStoryState)
          .catch(() => null);
      } catch (err) {
        setError('Failed to process your choice. Please try again.');
        setSelectedChoice(undefined);
        setStatusMsg('');
      } finally {
        setIsLoading(false);
        processingRef.current = false;
      }
    },
    [sessionId]
  );

  // ─── Voice Recording ────────────────────────────────────────────────────

  const handleRecordingComplete = useCallback(
    async (blob: Blob) => {
      if (!sessionId) return;
      setIsRecording(false);
      setStatusMsg('Transcribing your voice…');
      setError(null);

      try {
        const result = await transcribeAudio(blob, sessionId);
        setTranscription(result);
        setStatusMsg(`Heard: "${result.transcript}" (${(result.confidence * 100).toFixed(0)}%)`);

        if (narration && result.transcript) {
          const matchedId = matchTranscriptToChoice(result.transcript, narration.choices);
          if (matchedId) {
            setStatusMsg(`Matched choice — proceeding…`);
            setTimeout(() => handleChoiceSelect(matchedId), 500);
          } else {
            setStatusMsg(`Could not match "${result.transcript}" to a choice. Click a button below.`);
          }
        }
      } catch {
        setError('Transcription failed. Please try clicking a choice instead.');
        setStatusMsg('');
      }
    },
    [sessionId, narration, handleChoiceSelect]
  );

  // ─── Reset ──────────────────────────────────────────────────────────────

  const handleReset = useCallback(async () => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    localStorage.setItem('voxquest_session_id', newSessionId);
    setNarration(null);
    setStoryState(null);
    setTranscription(null);
    setSelectedChoice(undefined);
    setCharacterName('');
    setError(null);
    setStatusMsg('');
    setScreen('start');

    try {
      await resetSession(sessionId);
    } catch {
      // Ignore reset errors — new session already created
    }
  }, [sessionId]);

  // ─── Screens ─────────────────────────────────────────────────────────────

  // ── Start Screen ──────────────────────────────────────────────────────────
  if (screen === 'start') {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center bg-rpg-dark px-4">
        <div className="w-full max-w-md flex flex-col items-center gap-8">
          {/* Title */}
          <div className="text-center">
            <h1 className="rpg-title text-5xl font-extrabold mb-2">VoxQuest AI</h1>
            <p className="text-rpg-text-dim text-sm tracking-wide">
              Speak your destiny. Shape the story.
            </p>
          </div>

          {/* Character form */}
          <div className="rpg-panel w-full p-8 flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <label htmlFor="character-name" className="text-xs uppercase tracking-widest text-rpg-text-dim">
                Your Hero&apos;s Name
              </label>
              <input
                id="character-name"
                type="text"
                value={characterName}
                onChange={(e) => setCharacterName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleBeginQuest()}
                placeholder="Enter your name…"
                maxLength={30}
                className="bg-rpg-dark border border-rpg-border rounded-lg px-4 py-3 text-rpg-text placeholder:text-rpg-text-dim/50 focus:outline-none focus:ring-2 focus:ring-rpg-accent/50 focus:border-rpg-accent text-base"
              />
            </div>

            {error && (
              <p className="text-rpg-danger text-sm bg-rpg-danger/10 border border-rpg-danger/30 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              onClick={handleBeginQuest}
              disabled={!characterName.trim() || isLoading}
              className={clsx(
                'flex items-center justify-center gap-2 w-full py-4 rounded-lg font-bold text-base tracking-wide transition-all duration-200',
                characterName.trim() && !isLoading
                  ? 'bg-rpg-accent text-black hover:bg-rpg-accent/90 hover:scale-[1.02] shadow-[0_0_20px_rgba(212,160,23,0.3)]'
                  : 'bg-rpg-border text-rpg-text-dim cursor-not-allowed'
              )}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Sword className="w-5 h-5" />
              )}
              {isLoading ? statusMsg : 'Begin Quest'}
            </button>
          </div>

          {/* Footer links */}
          <div className="flex gap-4 text-xs text-rpg-text-dim">
            <Link href="/dashboard" className="hover:text-rpg-accent transition-colors flex items-center gap-1">
              <BarChart2 className="w-3.5 h-3.5" />
              Benchmarks
            </Link>
          </div>
        </div>
      </main>
    );
  }

  // ── End Screen ────────────────────────────────────────────────────────────
  if (screen === 'end') {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center bg-rpg-dark px-4">
        <div className="w-full max-w-lg flex flex-col items-center gap-8 text-center">
          <div>
            <p className="text-6xl mb-4">⚔️</p>
            <h1 className="rpg-title text-4xl font-extrabold mb-2">Quest Complete</h1>
            <p className="text-rpg-text-dim">
              Your legend ends here, {storyState?.character_name ?? characterName}.
            </p>
          </div>

          {narration && (
            <div className="rpg-panel w-full p-6">
              <p className="text-rpg-text leading-relaxed">{narration.narration_text}</p>
            </div>
          )}

          {storyState && (
            <div className="flex gap-6 text-sm">
              <span className="text-rpg-text-dim">
                Nodes visited: <span className="text-rpg-accent">{storyState.visited_nodes.length}</span>
              </span>
              <span className="text-rpg-text-dim">
                Health: <span className="text-rpg-accent">{storyState.health}</span>
              </span>
            </div>
          )}

          <button
            onClick={handleReset}
            className="flex items-center gap-2 bg-rpg-accent text-black font-bold px-8 py-3 rounded-lg hover:bg-rpg-accent/90 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            Play Again
          </button>
        </div>
      </main>
    );
  }

  // ── Game Screen ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-rpg-dark">
      {/* ── Top Bar ──────────────────────────────────────────────────────── */}
      <header className="border-b border-rpg-border bg-rpg-surface/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <h1 className="rpg-title text-xl font-extrabold flex-shrink-0">VoxQuest AI</h1>

          <div className="flex-1 min-w-0">
            <SessionInfo sessionId={sessionId} storyState={storyState} />
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Link
              href="/dashboard"
              className="text-xs text-rpg-text-dim hover:text-rpg-accent flex items-center gap-1 px-2 py-1 rounded border border-rpg-border hover:border-rpg-accent/50 transition-colors"
            >
              <BarChart2 className="w-3.5 h-3.5" />
              Benchmarks
            </Link>
            <button
              onClick={handleReset}
              title="Reset / New Game"
              className="text-xs text-rpg-text-dim hover:text-rpg-danger flex items-center gap-1 px-2 py-1 rounded border border-rpg-border hover:border-rpg-danger/50 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Left Panel: Voice + Waveform ─────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <div className="rpg-panel p-6 flex flex-col items-center gap-6">
            <h2 className="text-xs uppercase tracking-widest text-rpg-text-dim self-start">
              Voice Input
            </h2>

            <VoiceRecorder
              sessionId={sessionId}
              disabled={isLoading || !narration || narration.is_ending}
              onRecordingStart={() => setIsRecording(true)}
              onRecordingComplete={handleRecordingComplete}
            />

            <WaveformVisualizer isActive={isRecording} />

            {/* Transcription display */}
            {transcription && (
              <div className="w-full bg-rpg-dark rounded-lg border border-rpg-border p-3 animate-fade-in">
                <p className="text-xs uppercase tracking-widest text-rpg-text-dim mb-1">
                  Transcription
                </p>
                <p className="text-rpg-text text-sm italic">
                  &ldquo;{transcription.transcript}&rdquo;
                </p>
                <div className="flex gap-4 mt-2 text-xs text-rpg-text-dim">
                  <span>Confidence: {(transcription.confidence * 100).toFixed(0)}%</span>
                  <span>Lang: {transcription.language}</span>
                  <span>{transcription.processing_time_ms.toFixed(0)} ms</span>
                </div>
              </div>
            )}
          </div>

          {/* ── Voice Instructions ─────────────────────────────────────── */}
          <div className="rpg-panel p-4">
            <h3 className="text-xs uppercase tracking-widest text-rpg-text-dim mb-3">
              How to play
            </h3>
            <ul className="text-xs text-rpg-text-dim space-y-1.5">
              <li className="flex gap-2">
                <span className="text-rpg-accent">1.</span>
                Press the microphone button and speak your choice
              </li>
              <li className="flex gap-2">
                <span className="text-rpg-accent">2.</span>
                Say a number (&quot;one&quot;, &quot;two&quot;, &quot;three&quot;) or describe your action
              </li>
              <li className="flex gap-2">
                <span className="text-rpg-accent">3.</span>
                Or click a choice button directly
              </li>
              <li className="flex gap-2">
                <span className="text-rpg-accent">4.</span>
                Press &quot;Listen&quot; on the story panel to hear narration
              </li>
            </ul>
          </div>
        </div>

        {/* ── Right Panel: Story + Choices ─────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <div className="rpg-panel p-6 flex flex-col gap-4 min-h-[280px]">
            <h2 className="text-xs uppercase tracking-widest text-rpg-text-dim">
              The Story
            </h2>
            <StoryNarrator narration={narration} isLoading={isLoading} />
          </div>

          {narration && !narration.is_ending && (
            <div className="rpg-panel p-6">
              <ChoiceButtons
                choices={narration.choices}
                onChoiceSelect={handleChoiceSelect}
                disabled={isLoading}
                selectedChoice={selectedChoice}
              />
            </div>
          )}

          {narration?.is_ending && (
            <div className="rpg-panel p-6 text-center">
              <p className="text-rpg-text-dim mb-4">Your story has reached its conclusion.</p>
              <button
                onClick={() => setScreen('end')}
                className="bg-rpg-accent text-black font-bold px-6 py-2 rounded-lg hover:bg-rpg-accent/90 transition-all"
              >
                View Epilogue
              </button>
            </div>
          )}
        </div>
      </main>

      {/* ── Bottom Status Bar ─────────────────────────────────────────────── */}
      <footer className="border-t border-rpg-border bg-rpg-surface/60 px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <p
            className={clsx(
              'text-xs transition-all',
              error ? 'text-rpg-danger' : 'text-rpg-text-dim'
            )}
          >
            {error ?? statusMsg ?? 'Ready'}
          </p>
          {isLoading && (
            <Loader2 className="w-3.5 h-3.5 text-rpg-accent animate-spin flex-shrink-0" />
          )}
        </div>
      </footer>
    </div>
  );
}
