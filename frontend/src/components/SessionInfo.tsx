'use client';

import clsx from 'clsx';
import { Heart, Users, Package } from 'lucide-react';
import type { StoryState } from '@/types';

interface SessionInfoProps {
  sessionId: string;
  storyState: StoryState | null;
}

function HealthBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center gap-2">
      <Heart className="w-3.5 h-3.5 text-rpg-danger flex-shrink-0" />
      <div className="w-20 h-2 bg-rpg-border rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-500',
            pct > 60 ? 'bg-rpg-success' : pct > 30 ? 'bg-yellow-500' : 'bg-rpg-danger'
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-rpg-text-dim">{pct}</span>
    </div>
  );
}

export default function SessionInfo({ sessionId, storyState }: SessionInfoProps) {
  const shortId = sessionId.slice(0, 8);

  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      {/* Session ID */}
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-rpg-success animate-pulse" />
        <span className="text-rpg-text-dim text-xs font-mono">
          {shortId}…
        </span>
      </div>

      {storyState ? (
        <>
          {/* Character name */}
          <span className="text-rpg-accent font-semibold text-sm">
            {storyState.character_name}
          </span>

          {/* Health */}
          <HealthBar value={storyState.health} />

          {/* Relationship */}
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-rpg-info" />
            <span className="text-xs text-rpg-text-dim">
              {storyState.relationship_score > 0 ? '+' : ''}
              {storyState.relationship_score}
            </span>
          </div>

          {/* Inventory */}
          {storyState.inventory.length > 0 && (
            <div className="flex items-center gap-1.5">
              <Package className="w-3.5 h-3.5 text-rpg-accent-dim" />
              <div className="flex flex-wrap gap-1">
                {storyState.inventory.slice(0, 3).map((item) => (
                  <span
                    key={item}
                    title={item}
                    className="text-xs bg-rpg-accent/10 border border-rpg-accent/20 text-rpg-accent rounded px-1.5 py-0.5 max-w-[80px] truncate"
                  >
                    {item}
                  </span>
                ))}
                {storyState.inventory.length > 3 && (
                  <span className="text-xs text-rpg-text-dim">
                    +{storyState.inventory.length - 3}
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <span className="text-rpg-text-dim text-xs opacity-60">No active session</span>
      )}
    </div>
  );
}
