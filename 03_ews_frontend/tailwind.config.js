/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        sage: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
      },
      boxShadow: {
        'hard':    '4px 4px 0px 0px rgba(23,23,23,1)',
        'hard-sm': '2px 2px 0px 0px rgba(23,23,23,1)',
        'hard-lg': '6px 6px 0px 0px rgba(23,23,23,1)',
        'hard-xl': '8px 8px 0px 0px rgba(23,23,23,1)',
      },
      borderColor: {
        DEFAULT: 'rgba(23,23,23,1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.25s ease forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
