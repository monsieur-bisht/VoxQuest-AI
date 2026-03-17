'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, Play, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

import BenchmarkDashboard from '@/components/BenchmarkDashboard';
import { getBenchmarkMetrics, getBenchmarkResults, runBenchmark } from '@/lib/api';
import type { MetricsData, BenchmarkResult } from '@/types';

const AVAILABLE_MODELS = [
  'whisper-base',
  'whisper-small',
  'whisper-medium',
  'whisper-large',
  'whisper-large-v2',
];

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [results, setResults] = useState<BenchmarkResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedModel, setSelectedModel] = useState(AVAILABLE_MODELS[0]);
  const [error, setError] = useState<string | null>(null);
  const [runSuccess, setRunSuccess] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [m, r] = await Promise.all([getBenchmarkMetrics(), getBenchmarkResults()]);
      setMetrics(m);
      setResults(r);
    } catch {
      setError('Could not load benchmark data. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRunBenchmark = async () => {
    setIsRunning(true);
    setError(null);
    setRunSuccess(null);
    try {
      const result = await runBenchmark(selectedModel);
      setResults((prev) => [result, ...prev]);
      setRunSuccess(
        `Benchmark complete: ${result.model_name} — WER ${(result.avg_wer * 100).toFixed(1)}%`
      );
      // Refresh metrics
      getBenchmarkMetrics().then(setMetrics).catch(() => null);
    } catch {
      setError('Benchmark run failed. Please check the backend logs.');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-rpg-dark">
      {/* Header */}
      <header className="border-b border-rpg-border bg-rpg-surface/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-1.5 text-sm text-rpg-text-dim hover:text-rpg-accent transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Game
            </Link>
            <span className="text-rpg-border">|</span>
            <h1 className="rpg-title text-xl font-extrabold">
              Benchmark Dashboard
            </h1>
          </div>

          <button
            onClick={fetchData}
            disabled={isLoading}
            aria-label="Refresh data"
            className="p-2 rounded-lg border border-rpg-border text-rpg-text-dim hover:border-rpg-accent hover:text-rpg-accent transition-colors"
          >
            <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} />
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 flex flex-col gap-8">
        {/* Run Benchmark Panel */}
        <div className="rpg-panel p-6">
          <h2 className="text-sm font-semibold text-rpg-text mb-4 uppercase tracking-widest">
            Run Benchmark
          </h2>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex flex-col gap-1 flex-1">
              <label
                htmlFor="model-select"
                className="text-xs text-rpg-text-dim uppercase tracking-widest"
              >
                Model
              </label>
              <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={isRunning}
                className="bg-rpg-dark border border-rpg-border rounded-lg px-3 py-2 text-rpg-text text-sm focus:outline-none focus:ring-2 focus:ring-rpg-accent/50 focus:border-rpg-accent disabled:opacity-50"
              >
                {AVAILABLE_MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleRunBenchmark}
              disabled={isRunning}
              className={clsx(
                'flex items-center gap-2 px-6 py-2.5 rounded-lg font-semibold text-sm transition-all self-end sm:self-auto',
                isRunning
                  ? 'bg-rpg-border text-rpg-text-dim cursor-not-allowed'
                  : 'bg-rpg-accent text-black hover:bg-rpg-accent/90 shadow-[0_0_15px_rgba(212,160,23,0.25)]'
              )}
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Benchmark
                </>
              )}
            </button>
          </div>

          {/* Feedback messages */}
          {error && (
            <div className="mt-4 flex items-start gap-2 text-sm text-rpg-danger bg-rpg-danger/10 border border-rpg-danger/30 rounded-lg px-4 py-3">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}
          {runSuccess && (
            <div className="mt-4 text-sm text-rpg-success bg-rpg-success/10 border border-rpg-success/30 rounded-lg px-4 py-3">
              ✅ {runSuccess}
            </div>
          )}
        </div>

        {/* Results */}
        <div className="rpg-panel p-6">
          <h2 className="text-sm font-semibold text-rpg-text mb-6 uppercase tracking-widest">
            Results &amp; Metrics
          </h2>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-rpg-accent" />
            </div>
          ) : (
            <BenchmarkDashboard metrics={metrics} results={results} />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-rpg-border py-3 px-4 text-center text-xs text-rpg-text-dim">
        VoxQuest AI — Benchmark Dashboard
      </footer>
    </div>
  );
}
