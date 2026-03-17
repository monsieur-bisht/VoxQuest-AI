'use client';

import clsx from 'clsx';
import type { MetricsData, BenchmarkResult } from '@/types';

interface BenchmarkDashboardProps {
  metrics: MetricsData | null;
  results: BenchmarkResult[];
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="bg-rpg-surface border border-rpg-border rounded-xl p-4 flex flex-col gap-1">
      <p className="text-xs uppercase tracking-widest text-rpg-text-dim">{label}</p>
      <p className={clsx('text-2xl font-bold', accent ? 'text-rpg-accent' : 'text-rpg-text')}>
        {value}
      </p>
      {sub && <p className="text-xs text-rpg-text-dim">{sub}</p>}
    </div>
  );
}

export default function BenchmarkDashboard({ metrics, results }: BenchmarkDashboardProps) {
  if (!metrics && !results.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-rpg-text-dim">
        <p className="text-xl mb-2">No benchmark data yet</p>
        <p className="text-sm opacity-60">Run a benchmark to see results here</p>
      </div>
    );
  }

  const passRate = (r: BenchmarkResult) =>
    r.total_samples > 0 ? ((r.passed / r.total_samples) * 100).toFixed(1) : '—';

  return (
    <div className="flex flex-col gap-6">
      {/* Stats Cards */}
      {metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            label="Total Sessions"
            value={metrics.total_sessions}
            accent
          />
          <StatCard
            label="Avg WER"
            value={`${(metrics.avg_wer * 100).toFixed(1)}%`}
            sub="Word Error Rate"
          />
          <StatCard
            label="Avg Latency"
            value={`${metrics.avg_latency_ms.toFixed(0)} ms`}
            sub="Processing time"
          />
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-rpg-surface border border-rpg-border rounded-xl p-4 animate-pulse h-20" />
          ))}
        </div>
      )}

      {/* Top Languages */}
      {metrics?.top_languages?.length ? (
        <div>
          <h3 className="text-xs uppercase tracking-widest text-rpg-text-dim mb-2">
            Top Languages
          </h3>
          <div className="flex flex-wrap gap-2">
            {metrics.top_languages.map((lang) => (
              <span
                key={lang}
                className="text-xs bg-rpg-info/20 text-rpg-info border border-rpg-info/30 rounded-full px-3 py-1"
              >
                {lang}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {/* Results Table */}
      {results.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-widest text-rpg-text-dim mb-3">
            Benchmark Results
          </h3>
          <div className="overflow-x-auto rounded-lg border border-rpg-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-rpg-surface text-rpg-text-dim text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Model</th>
                  <th className="px-4 py-3 text-right">WER</th>
                  <th className="px-4 py-3 text-right">CER</th>
                  <th className="px-4 py-3 text-right">Latency</th>
                  <th className="px-4 py-3 text-right">Pass Rate</th>
                  <th className="px-4 py-3 text-right">Samples</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, idx) => (
                  <tr
                    key={r.run_id}
                    className={clsx(
                      'border-t border-rpg-border transition-colors',
                      idx % 2 === 0 ? 'bg-rpg-dark' : 'bg-rpg-surface',
                      'hover:bg-rpg-accent/5'
                    )}
                  >
                    <td className="px-4 py-3 text-rpg-text font-medium">{r.model_name}</td>
                    <td className="px-4 py-3 text-right text-rpg-text-dim">
                      {(r.avg_wer * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right text-rpg-text-dim">
                      {(r.avg_cer * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right text-rpg-text-dim">
                      {r.avg_latency_ms.toFixed(0)} ms
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={clsx(
                          'inline-block rounded-full px-2 py-0.5 text-xs font-semibold',
                          parseFloat(passRate(r)) >= 80
                            ? 'bg-rpg-success/20 text-rpg-success'
                            : 'bg-rpg-danger/20 text-rpg-danger'
                        )}
                      >
                        {passRate(r)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-rpg-text-dim">{r.total_samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Language Breakdown for latest result */}
      {results[0] && Object.keys(results[0].results_by_language).length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-widest text-rpg-text-dim mb-3">
            Language Breakdown — {results[0].model_name}
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(results[0].results_by_language).map(([lang, stats]) => (
              <div key={lang} className="bg-rpg-surface border border-rpg-border rounded-lg p-3">
                <p className="text-xs font-bold text-rpg-accent uppercase">{lang}</p>
                <p className="text-xs text-rpg-text-dim mt-1">
                  WER: {(stats.wer * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-rpg-text-dim">
                  CER: {(stats.cer * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-rpg-text-dim">Samples: {stats.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
