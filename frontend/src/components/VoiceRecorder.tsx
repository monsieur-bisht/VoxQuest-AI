'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import type { RecordingState } from '@/types';
import { formatDuration } from '@/lib/audio';

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  onRecordingStart?: () => void;
  disabled?: boolean;
  sessionId: string;
}

export default function VoiceRecorder({
  onRecordingComplete,
  onRecordingStart,
  disabled = false,
  sessionId,
}: VoiceRecorderProps) {
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Clear timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        setRecordingState('processing');
        onRecordingComplete(blob);
      };

      recorder.start(100);
      setDuration(0);
      setRecordingState('recording');
      onRecordingStart?.();

      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (err) {
      setError('Microphone access denied. Please allow microphone permissions.');
      setRecordingState('error');
    }
  }, [onRecordingComplete, onRecordingStart]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const handleClick = () => {
    if (disabled) return;
    if (recordingState === 'recording') {
      stopRecording();
    } else if (recordingState === 'idle' || recordingState === 'done' || recordingState === 'error') {
      startRecording();
    }
  };

  // Reset to idle after processing completes (parent sets disabled=false)
  useEffect(() => {
    if (!disabled && recordingState === 'processing') {
      setRecordingState('done');
    }
  }, [disabled, recordingState]);

  useEffect(() => {
    if (recordingState === 'done') {
      const t = setTimeout(() => setRecordingState('idle'), 1500);
      return () => clearTimeout(t);
    }
  }, [recordingState]);

  const statusText: Record<RecordingState, string> = {
    idle: 'Click to speak',
    recording: `Recording… ${formatDuration(duration)}`,
    processing: 'Processing…',
    done: 'Done!',
    error: error ?? 'Error',
  };

  const isRecording = recordingState === 'recording';
  const isProcessing = recordingState === 'processing';
  const isDisabled = disabled || isProcessing;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Record Button */}
      <button
        onClick={handleClick}
        disabled={isDisabled}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        className={clsx(
          'relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-rpg-accent/50',
          isRecording
            ? 'bg-rpg-danger shadow-[0_0_30px_rgba(192,57,43,0.6)] scale-110'
            : isProcessing
            ? 'bg-rpg-accent-dim cursor-not-allowed'
            : isDisabled
            ? 'bg-rpg-border cursor-not-allowed opacity-50'
            : 'bg-rpg-surface border-2 border-rpg-accent hover:bg-rpg-accent/20 hover:scale-105 cursor-pointer'
        )}
      >
        {/* Pulse rings when recording */}
        {isRecording && (
          <>
            <span className="absolute inset-0 rounded-full bg-rpg-danger/30 animate-ping" />
            <span className="absolute inset-[-8px] rounded-full border border-rpg-danger/40 animate-pulse" />
          </>
        )}

        {isProcessing ? (
          <Loader2 className="w-10 h-10 text-rpg-accent animate-spin" />
        ) : isRecording ? (
          <MicOff className="w-10 h-10 text-white" />
        ) : (
          <Mic
            className={clsx(
              'w-10 h-10',
              isDisabled ? 'text-rpg-text-dim' : 'text-rpg-accent'
            )}
          />
        )}
      </button>

      {/* Status text */}
      <p
        className={clsx(
          'text-sm font-medium tracking-wide transition-colors',
          recordingState === 'error'
            ? 'text-rpg-danger'
            : recordingState === 'done'
            ? 'text-rpg-success'
            : isRecording
            ? 'text-rpg-danger'
            : 'text-rpg-text-dim'
        )}
      >
        {statusText[recordingState]}
      </p>

      {/* Session ID hint */}
      <p className="text-xs text-rpg-text-dim opacity-60">
        Session: {sessionId.slice(0, 8)}…
      </p>
    </div>
  );
}
