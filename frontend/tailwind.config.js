/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1677FF',
        success: '#52C41A',
        warning: '#FAAD14',
        danger: '#FF4D4F',
        background: '#F5F7FA',
        card: '#FFFFFF',
        border: '#E5E7EB',
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'sans-serif'],
      },
      animation: {
        'breathe': 'breathe 3s ease-in-out infinite',
        'scan': 'scan 2s linear',
        'blink': 'blink 0.5s ease-in-out',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '0.7', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        scan: {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(100%)' },
        },
        blink: {
          '0%, 100%': { backgroundColor: 'transparent' },
          '50%': { backgroundColor: 'rgba(82, 196, 26, 0.2)' },
        },
      },
    },
  },
  plugins: [],
}

