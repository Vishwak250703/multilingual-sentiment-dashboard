/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Primary brand palette
        brand: {
          50:  '#f0f0ff',
          100: '#e0e0ff',
          200: '#c4b5fd',
          300: '#a78bfa',
          400: '#8b5cf6',
          500: '#7c3aed',
          600: '#6d28d9',
          700: '#5b21b6',
          800: '#4c1d95',
          900: '#2e1065',
        },
        // Neon accent
        neon: {
          purple: '#c084fc',
          blue:   '#60a5fa',
          cyan:   '#22d3ee',
          green:  '#4ade80',
          pink:   '#f472b6',
        },
        // Dark backgrounds
        dark: {
          900: '#0a0a0f',
          800: '#0f0f1a',
          700: '#14142b',
          600: '#1a1a35',
          500: '#22223f',
          400: '#2d2d52',
        },
        // Glass surface
        glass: {
          DEFAULT: 'rgba(255,255,255,0.05)',
          border:  'rgba(255,255,255,0.10)',
          hover:   'rgba(255,255,255,0.08)',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-brand': 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
        'gradient-neon': 'linear-gradient(135deg, #c084fc 0%, #60a5fa 100%)',
        'gradient-dark': 'linear-gradient(180deg, #0a0a0f 0%, #14142b 100%)',
      },
      boxShadow: {
        'glass': '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
        'glass-hover': '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15)',
        'neon-purple': '0 0 20px rgba(139,92,246,0.4)',
        'neon-blue':   '0 0 20px rgba(96,165,250,0.4)',
        'neon-glow':   '0 0 40px rgba(139,92,246,0.2)',
      },
      backdropBlur: {
        xs: '2px',
        glass: '12px',
        heavy: '24px',
      },
      animation: {
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.4s ease-out',
        'slide-in':   'slideIn 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'counter':    'counter 1s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%':   { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(139,92,246,0.3)' },
          '50%':      { boxShadow: '0 0 40px rgba(139,92,246,0.6)' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
