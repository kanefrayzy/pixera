/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
    './generate/templates/**/*.html',
    './gallery/templates/**/*.html',
    './dashboard/templates/**/*.html',
    './blog/templates/**/*.html',
    './pages/templates/**/*.html',
  ],
  safelist: [
    // Modal and drawer arbitrary values
    'max-w-[min(95vw,420px)]',
    'max-h-[min(90vh,650px)]',
    'max-h-[min(95vh,800px)]',
    'max-w-[min(90vw,500px)]',
    'max-w-[80px]',

    // CSS variable classes - backgrounds
    'bg-[var(--bg)]',
    'bg-[var(--card)]',
    'bg-[var(--bg-card)]',
    'bg-[var(--mobilemenu)]',

    // CSS variable classes - text colors
    'text-[var(--text)]',
    'text-[var(--muted)]',
    'hover:text-[var(--text)]',
    'group-hover:text-primary',

    // CSS variable classes - borders
    'border-[var(--bord)]',
    'border-[var(--bord)]/20',
    'ring-[var(--bord)]',

    // Opacity classes - black backgrounds
    'bg-black/[.02]',
    'bg-black/[.03]',
    'bg-black/[.04]',
    'bg-black/[.08]',
    'bg-black/5',
    'bg-black/70',
    'bg-black/80',
    'hover:bg-black/[.03]',
    'hover:bg-black/[.04]',
    'hover:bg-black/10',
    'dark:bg-black/80',
    'from-black/[.02]',

    // Opacity classes - white backgrounds
    'bg-white/0',
    'bg-white/5',
    'bg-white/10',
    'bg-white/30',
    'bg-white/70',
    'dark:bg-white/[.02]',
    'dark:bg-white/[.03]',
    'dark:bg-white/5',
    'dark:bg-white/10',
    'bg-white/30',
    'hover:bg-white/10',
    'dark:hover:bg-white/[.03]',
    'dark:hover:bg-white/10',
    'dark:from-white/[.02]',
    'ring-white/10',
    'dark:ring-white/10',
    'ring-black/5',

    // Shadows
    'shadow-[0_8px_30px_rgba(0,0,0,0.18)]',

    // Interactive states
    'active:scale-[.98]',
    'active:scale-95',
    'selection:bg-primary/30',
    'selection:text-[var(--bg)]',

    // Focus states
    'focus:border-primary/60',
    'focus:ring-primary/60',
    'focus:ring-primary/30',
    'focus:ring-2',
    'focus-visible:ring-2',
    'focus-visible:ring-primary/60',
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: '0.75rem' },
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1120px',
        '2xl': '1280px'
      }
    },
    extend: {
      screens: {
        xs: '320px'
      },
      colors: {
        primary: '#01D1FB',
        accent: '#01D1FB',
        darkbg: '#0B0E14',
        lightbg: '#F7F8FA',
        ink: '#0F172A',
        mobilemenu: {
          light: '#FFFFFF',
          dark: '#1A1F2E'
        }
      },
      boxShadow: {
        soft: '0 8px 30px rgba(0,0,0,.18)',
        ring: '0 0 0 2px rgba(1,209,251,.4)'
      },
      dropShadow: {
        glow: '0 10px 25px rgba(1,209,251,.5)'
      },
      backdropBlur: {
        xs: '2px'
      },
      fontSize: {
        lg: ['1rem', { lineHeight: '1rem' }]
      }
    },
    fontFamily: {
      sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'Apple Color Emoji', 'Segoe UI Emoji']
    }
  },
  plugins: []
}
