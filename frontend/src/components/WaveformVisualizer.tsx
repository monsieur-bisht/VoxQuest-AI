'use client';

import { useEffect, useRef } from 'react';
import { generateWaveformData, createAudioContext } from '@/lib/audio';

interface WaveformVisualizerProps {
  isActive: boolean;
  audioBlob?: Blob;
}

const BAR_COUNT = 32;

export default function WaveformVisualizer({ isActive, audioBlob }: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | MediaBufferSourceNode | null>(null);

  // Draw idle / static animation
  useEffect(() => {
    if (isActive) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let frame = 0;

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      frame++;

      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      const barWidth = width / BAR_COUNT - 2;
      for (let i = 0; i < BAR_COUNT; i++) {
        // Gentle idle wave
        const amp = 0.08 + 0.06 * Math.sin((frame * 0.05) + (i * 0.4));
        const barHeight = height * amp;
        const x = i * (barWidth + 2);
        const y = (height - barHeight) / 2;

        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        gradient.addColorStop(0, 'rgba(45, 212, 191, 0.4)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.2)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }
    };

    draw();
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isActive]);

  // Live microphone visualization
  useEffect(() => {
    if (!isActive) return;

    let mounted = true;

    const init = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!mounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        const audioCtx = createAudioContext();
        audioCtxRef.current = audioCtx;

        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;
        dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);

        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        sourceRef.current = source as unknown as MediaBufferSourceNode;

        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const draw = () => {
          if (!mounted) return;
          animationRef.current = requestAnimationFrame(draw);

          const bars = generateWaveformData(analyser, dataArrayRef.current!);
          const { width, height } = canvas;
          ctx.clearRect(0, 0, width, height);

          const barWidth = width / BAR_COUNT - 2;
          bars.forEach((amp, i) => {
            const barHeight = Math.max(4, height * amp * 0.9);
            const x = i * (barWidth + 2);
            const y = (height - barHeight) / 2;

            const intensity = Math.min(1, amp * 2);
            const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
            gradient.addColorStop(0, `rgba(45, 212, 191, ${0.6 + intensity * 0.4})`);
            gradient.addColorStop(1, `rgba(16, 185, 129, ${0.3 + intensity * 0.4})`);
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, barHeight, 2);
            ctx.fill();
          });
        };

        draw();

        // cleanup stream tracks when not active
        stream.getAudioTracks().forEach((t) => {
          t.addEventListener('ended', () => {
            if (mounted) {
              // track ended externally (e.g. MediaRecorder stopped)
            }
          });
        });
      } catch {
        // Microphone not available; visualizer stays idle
      }
    };

    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    init();

    return () => {
      mounted = false;
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      audioCtxRef.current?.close();
      audioCtxRef.current = null;
    };
  }, [isActive]);

  return (
    <div className="w-full h-16 rounded-lg bg-rpg-surface border border-rpg-border overflow-hidden">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        width={320}
        height={64}
        aria-label="Audio waveform visualizer"
      />
    </div>
  );
}
