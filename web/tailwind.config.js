/** @type {import('tailwindcss').Config} */

// ─── Theme tokens ─────────────────────────────────────────────────────────────
// Edit colours here. Components use the semantic names below (bg-accent, etc).
// The prose styles in index.css reference the same values — update both if you
// change a colour.
const colors = {
  surface:       '#0b0d12',
  sidebar:       '#101521',
  panel:         '#111827',
  border:        '#1f2937',
  'border-faint':'#1a2234',
  text:          '#e6edf7',
  muted:         '#9aa7b6',
  faint:         '#5a6a7a',
  accent:        '#63e6be',
  'accent-hover':'#4dd4a8',
  'accent-faint':'rgba(99,230,190,0.12)',
  teal:          '#63e6be',
  sky:           '#7c9eff',
}

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors,
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
