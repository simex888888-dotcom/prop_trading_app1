/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0A0A0F',
          secondary: '#12121A',
          card: '#16161F',
          border: '#1E1E2E',
        },
        brand: {
          primary: '#6C63FF',
          secondary: '#00D4AA',
          glow: 'rgba(108, 99, 255, 0.4)',
        },
        profit: '#00D4AA',
        loss: '#FF4757',
        warning: '#FFA502',
        text: {
          primary: '#FFFFFF',
          secondary: '#8B8B9A',
          muted: '#4A4A5A',
        },
      },
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px rgba(108, 99, 255, 0.3)',
        'glow-profit': '0 0 15px rgba(0, 212, 170, 0.4)',
        'glow-loss': '0 0 15px rgba(255, 71, 87, 0.4)',
        glass: '0 8px 32px rgba(0, 0, 0, 0.4)',
      },
      backdropBlur: {
        glass: '12px',
      },
      animation: {
        'count-up': 'countUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        shake: 'shake 0.5s ease-in-out',
      },
      keyframes: {
        countUp: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(108, 99, 255, 0.3)' },
          '50%': { boxShadow: '0 0 30px rgba(108, 99, 255, 0.6)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
      },
    },
  },
  plugins: [],
}
