'use client';

import { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2 } from 'lucide-react';
import clsx from 'clsx';
import type { StoryNarration } from '@/types';
import { synthesizeSpeech } from '@/lib/api';
import { playAudioBlob } from '@/lib/audio';

interface StoryNarratorProps {
  narration: StoryNarration | null;
  isLoading: boolean;
}

const TONE_CONFIG: Record<string, { emoji: string; color: string; label: string }> = {
  neutral: { emoji: '⚖️', color: 'text-rpg-text-dim', label: 'Neutral' },
  tense: { emoji: '⚔️', color: 'text-red-400', label: 'Tense' },
  joyful: { emoji: '✨', color: 'text-yellow-300', label: 'Joyful' },
  mysterious: { emoji: '🌙', color: 'text-purple-400', label: 'Mysterious' },
  dramatic: { emoji: '🌩️', color: 'text-orange-400', label: 'Dramatic' },
  peaceful: { emoji: '🌿', color: 'text-green-400', label: 'Peaceful' },
};

function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    setDisplayed('');
    indexRef.current = 0;
    const interval = setInterval(() => {
      indexRef.current++;
      setDisplayed(text.slice(0, indexRef.current));
      if (indexRef.current >= text.length) clearInterval(interval);
    }, 18);
    return () => clearInterval(interval);
  }, [text]);

  return <span>{displayed}</span>;
}

export default function StoryNarrator({ narration, isLoading }: StoryNarratorProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const audioBlobRef = useRef<Blob | null>(null);
  const prevNodeRef = useRef<string | null>(null);

  // Prefetch TTS when narration changes
  useEffect(() => {
    if (!narration) return;
    if (narration.node_id === prevNodeRef.current) return;
    prevNodeRef.current = narration.node_id;
    audioBlobRef.current = null;
    setTtsError(null);

    synthesizeSpeech(narration.narration_text)
      .then((blob) => {
        audioBlobRef.current = blob;
      })
      .catch(() => {
        setTtsError('TTS unavailable');
      });
  }, [narration]);

  const handlePlayPause = async () => {
    if (isPlaying) return;
    if (!narration) return;
    setIsPlaying(true);
    try {
      const blob = audioBlobRef.current ?? (await synthesizeSpeech(narration.narration_text));
      audioBlobRef.current = blob;
      await playAudioBlob(blob);
    } catch {
      setTtsError('Could not play audio');
    } finally {
      setIsPlaying(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 animate-pulse">
        <div className="h-4 bg-rpg-border rounded w-1/4" />
        <div className="h-4 bg-rpg-border rounded w-full" />
        <div className="h-4 bg-rpg-border rounded w-5/6" />
        <div className="h-4 bg-rpg-border rounded w-4/6" />
        <div className="h-4 bg-rpg-border rounded w-3/4" />
      </div>
    );
  }

  if (!narration) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-rpg-text-dim">
        <p className="text-lg">Your adventure awaits…</p>
        <p className="text-sm mt-2 opacity-60">Enter your name and begin the quest</p>
      </div>
    );
  }

  const tone = TONE_CONFIG[narration.emotional_tone] ?? TONE_CONFIG.neutral;

  return (
    <div className="flex flex-col gap-4 animate-fade-in">
      {/* Tone + audio row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">{tone.emoji}</span>
          <span className={clsx('text-xs font-semibold uppercase tracking-widest', tone.color)}>
            {tone.label}
          </span>
          {narration.is_ending && (
            <span className="ml-2 text-xs bg-rpg-accent/20 text-rpg-accent border border-rpg-accent/40 rounded-full px-2 py-0.5">
              Ending
            </span>
          )}
        </div>

        {/* TTS Controls */}
        <button
          onClick={handlePlayPause}
          disabled={isPlaying}
          aria-label={isPlaying ? 'Playing narration' : 'Play narration'}
          className={clsx(
            'flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors',
            isPlaying
              ? 'border-rpg-accent/60 text-rpg-accent bg-rpg-accent/10 cursor-not-allowed'
              : 'border-rpg-border text-rpg-text-dim hover:border-rpg-accent hover:text-rpg-accent'
          )}
        >
          {isPlaying ? (
            <>
              <Pause className="w-3 h-3" />
              Playing…
            </>
          ) : (
            <>
              <Play className="w-3 h-3" />
              Listen
            </>
          )}
          <Volume2 className="w-3 h-3 ml-1 opacity-60" />
        </button>
      </div>

      {ttsError && (
        <p className="text-xs text-rpg-text-dim opacity-60">{ttsError}</p>
      )}

      {/* Narration text */}
      <div className="bg-rpg-surface rounded-lg border border-rpg-border p-4 min-h-[120px]">
        <p className="text-rpg-text leading-relaxed text-base">
          <TypewriterText key={narration.node_id} text={narration.narration_text} />
        </p>
      </div>

      {/* Node ID badge */}
      <p className="text-xs text-rpg-text-dim opacity-40 text-right">
        Node: {narration.node_id}
      </p>
    </div>
  );
}
