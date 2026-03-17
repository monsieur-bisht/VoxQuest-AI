/**
 * Reads frequency data from an AnalyserNode and returns normalized bar heights.
 */
export function generateWaveformData(
  analyser: AnalyserNode,
  dataArray: Uint8Array
): number[] {
  analyser.getByteFrequencyData(dataArray);
  const bars = 32;
  const step = Math.floor(dataArray.length / bars);
  return Array.from({ length: bars }, (_, i) => {
    const slice = dataArray.slice(i * step, (i + 1) * step);
    const avg = slice.reduce((sum, v) => sum + v, 0) / slice.length;
    return avg / 255;
  });
}

export async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      resolve(result.split(',')[1] ?? result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export function createAudioContext(): AudioContext {
  return new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
}

export async function playAudioBlob(audioBlob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(audioBlob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(e);
    };
    audio.play().catch(reject);
  });
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
