/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0f172a',
          soft: '#111827',
          softer: '#020617',
        },
        primary: {
          DEFAULT: '#3b82f6',
          soft: '#60a5fa',
          softer: '#bfdbfe',
        },
      },
      boxShadow: {
        soft: '0 18px 45px rgba(15,23,42,0.75)',
      },
      borderRadius: {
        xl: '1rem',
      },
    },
  },
  plugins: [],
}

