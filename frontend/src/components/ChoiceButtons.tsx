'use client';

import { useState } from 'react';
import clsx from 'clsx';
import type { StoryChoice } from '@/types';

interface ChoiceButtonsProps {
  choices: StoryChoice[];
  onChoiceSelect: (choiceId: string) => void;
  disabled: boolean;
  selectedChoice?: string;
}

export default function ChoiceButtons({
  choices,
  onChoiceSelect,
  disabled,
  selectedChoice,
}: ChoiceButtonsProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (!choices.length) return null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs uppercase tracking-widest text-rpg-text-dim font-semibold">
        Choose your path
      </p>

      {choices.map((choice, index) => {
        const isSelected = selectedChoice === choice.choice_id;
        const isHovered = hoveredId === choice.choice_id;

        return (
          <div
            key={choice.choice_id}
            className="animate-slide-up"
            style={{ animationDelay: `${index * 80}ms`, animationFillMode: 'both' }}
          >
            <button
              onClick={() => !disabled && onChoiceSelect(choice.choice_id)}
              onMouseEnter={() => setHoveredId(choice.choice_id)}
              onMouseLeave={() => setHoveredId(null)}
              disabled={disabled}
              aria-pressed={isSelected}
              className={clsx(
                'w-full text-left px-4 py-3 rounded-lg border transition-all duration-200 group',
                'flex items-start gap-3',
                isSelected
                  ? 'border-rpg-accent bg-rpg-accent/15 text-rpg-text'
                  : disabled
                  ? 'border-rpg-border/40 text-rpg-text-dim cursor-not-allowed opacity-50 bg-rpg-surface'
                  : 'border-rpg-border text-rpg-text bg-rpg-surface hover:border-rpg-accent/70 hover:bg-rpg-accent/10 cursor-pointer'
              )}
            >
              {/* Number badge */}
              <span
                className={clsx(
                  'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 transition-colors',
                  isSelected
                    ? 'bg-rpg-accent text-black'
                    : 'bg-rpg-border text-rpg-text-dim group-hover:bg-rpg-accent/40 group-hover:text-rpg-accent'
                )}
              >
                {index + 1}
              </span>

              <div className="flex flex-col gap-1 min-w-0">
                <span className="text-sm font-medium leading-snug">{choice.text}</span>

                {/* Consequence preview — show on hover */}
                {choice.consequence_preview && (
                  <span
                    className={clsx(
                      'text-xs text-rpg-text-dim italic transition-all duration-200 overflow-hidden',
                      isHovered ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0'
                    )}
                  >
                    {choice.consequence_preview}
                  </span>
                )}

                {/* Voice hint */}
                <span className="text-xs text-rpg-text-dim opacity-50">
                  Say &quot;{index + 1}&quot; or &quot;{choice.text.split(' ').slice(0, 3).join(' ')}…&quot;
                </span>
              </div>
            </button>
          </div>
        );
      })}
    </div>
  );
}
