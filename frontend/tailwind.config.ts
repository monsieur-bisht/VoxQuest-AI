import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        'rpg-dark': '#0a0a0f',
        'rpg-surface': '#13131a',
        'rpg-border': '#2a2a3a',
        'rpg-accent': '#d4a017',
        'rpg-accent-dim': '#8b6914',
        'rpg-text': '#e8e0d0',
        'rpg-text-dim': '#9a9080',
        'rpg-danger': '#c0392b',
        'rpg-success': '#27ae60',
        'rpg-info': '#2980b9',
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'typewriter': 'typewriter 2s steps(40, end)',
        'fade-in': 'fadeIn 0.5s ease-in',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        typewriter: { from: { width: '0' }, to: { width: '100%' } },
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config
