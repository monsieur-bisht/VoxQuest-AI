"use client";

import { useEffect, useRef, useState } from "react";

type VoiceRecorderProps = {
  onRecorded: (blob: Blob) => void;
};

export function VoiceRecorder({ onRecorded }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);

  const drawWaveform = () => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const context = canvas.getContext("2d");
    if (!context) return;

    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(data);

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#4fd1ff";
    context.lineWidth = 2;
    context.beginPath();

    const slice = canvas.width / data.length;
    let x = 0;

    for (let i = 0; i < data.length; i += 1) {
      const v = data[i] / 128.0;
      const y = (v * canvas.height) / 2;
      if (i === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
      x += slice;
    }

    context.lineTo(canvas.width, canvas.height / 2);
    context.stroke();
    rafRef.current = requestAnimationFrame(drawWaveform);
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    analyserRef.current = analyser;

    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];

    recorder.ondataavailable = (event) => {
      chunksRef.current.push(event.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      onRecorded(blob);
      stream.getTracks().forEach((track) => track.stop());
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };

    mediaRecorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    drawWaveform();
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div className="recorder-card">
      <button onClick={recording ? stopRecording : startRecording} className="action-btn">
        {recording ? "Stop Recording" : "Start Recording"}
      </button>
      <canvas ref={canvasRef} width={420} height={96} className="waveform" />
    </div>
  );
}
