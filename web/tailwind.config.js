/** @type {import('tailwindcss').Config} */

// ─── Theme tokens ────────────────────────────────────────────────────────────
// Change colours here. All components reference these names.
const theme = {
  // Backgrounds
  surface:   '#f0ede6',   // main chat area
  sidebar:   '#e8e2d9',   // sidebar
  panel:     '#ffffff',   // message bubbles / cards
  input:     '#ffffff',   // input box

  // Borders
  border:    '#d6cfc4',
  borderFaint: '#e5e0d8',

  // Text
  text:      '#0d1117',   // primary
  muted:     '#6b7280',   // secondary
  faint:     '#9ca3af',   // placeholder / timestamps

  // Brand accents (from onkaul.cloud)
  accent:    '#ff7a59',   // coral — primary CTA, user bubbles
  accentHover: '#f56a47',
  accentFaint: '#fff0ed', // light tint for hover states
  teal:      '#63e6be',   // secondary accent
  blue:      '#7c9eff',   // tertiary accent
}

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface:      theme.surface,
        sidebar:      theme.sidebar,
        panel:        theme.panel,
        input:        theme.input,
        border:       theme.border,
        'border-faint': theme.borderFaint,
        text:         theme.text,
        muted:        theme.muted,
        faint:        theme.faint,
        accent:       theme.accent,
        'accent-hover': theme.accentHover,
        'accent-faint': theme.accentFaint,
        teal:         theme.teal,
        sky:          theme.blue,
      },
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      ringColor: {
        accent: theme.accent,
      },
    },
  },
  plugins: [],
}
