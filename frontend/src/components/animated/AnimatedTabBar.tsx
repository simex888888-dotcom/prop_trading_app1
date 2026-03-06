/**
 * AnimatedTabBar — нижняя навигация с профессиональными SVG-иконками.
 * Прилипает к низу с учётом safe-area-inset (iPhone notch).
 */
import { motion } from 'framer-motion'
import { useLocation, useNavigate } from 'react-router-dom'

// ── Premium SVG icons ──────────────────────────────────────────────────────────

function IconDashboard({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={active ? 2 : 1.6} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function IconTerminal({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={active ? 2 : 1.6} strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="3" x2="6" y2="21" />
      <rect x="4" y="7" width="4" height="7" rx="0.5" />
      <line x1="12" y1="5" x2="12" y2="21" />
      <rect x="10" y="9" width="4" height="6" rx="0.5" />
      <line x1="18" y1="2" x2="18" y2="20" />
      <rect x="16" y="6" width="4" height="8" rx="0.5" />
    </svg>
  )
}

function IconChallenges({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={active ? 2 : 1.6} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 21h8M12 17v4" />
      <path d="M17 4h2a2 2 0 0 1 2 2v1a4 4 0 0 1-4 4h-1" />
      <path d="M7 4H5a2 2 0 0 0-2 2v1a4 4 0 0 0 4 4h1" />
      <path d="M12 14c-4 0-7-3-7-7V4h14v3c0 4-3 7-7 7z" />
    </svg>
  )
}

function IconHistory({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={active ? 2 : 1.6} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 6 12 12 16.5 14.5" />
    </svg>
  )
}

function IconProfile({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={active ? 2 : 1.6} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-3.8 3.6-7 8-7s8 3.2 8 7" />
    </svg>
  )
}

// ── Tab config ─────────────────────────────────────────────────────────────────

interface Tab {
  path: string
  label: string
  Icon: React.FC<{ active: boolean }>
}

const TABS: Tab[] = [
  { path: '/dashboard',  label: 'Главная',  Icon: IconDashboard },
  { path: '/terminal',   label: 'Торговля', Icon: IconTerminal },
  { path: '/challenges', label: 'Планы',    Icon: IconChallenges },
  { path: '/history',    label: 'История',  Icon: IconHistory },
  { path: '/profile',    label: 'Профиль',  Icon: IconProfile },
]

// ── Component ──────────────────────────────────────────────────────────────────

export function AnimatedTabBar() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 shrink-0"
      style={{
        background: 'rgba(8,8,16,0.97)',
        backdropFilter: 'blur(28px)',
        WebkitBackdropFilter: 'blur(28px)',
        borderTop: '1px solid rgba(255,255,255,0.055)',
        paddingBottom: 'max(6px, env(safe-area-inset-bottom))',
      }}
    >
      <div className="flex items-center justify-around px-1 pt-2 pb-0.5">
        {TABS.map((tab) => {
          const isActive = location.pathname.startsWith(tab.path)
          return (
            <motion.button
              key={tab.path}
              className="flex flex-col items-center gap-0.5 rounded-2xl relative"
              style={{ minWidth: 52, padding: '5px 10px' }}
              onClick={() => navigate(tab.path)}
              whileTap={{ scale: 0.87 }}
            >
              {/* Active glow pill */}
              {isActive && (
                <motion.div
                  layoutId="tab-active-bg"
                  className="absolute inset-0 rounded-2xl"
                  style={{ background: 'rgba(108,99,255,0.13)' }}
                  transition={{ type: 'spring', stiffness: 450, damping: 38 }}
                />
              )}

              <motion.span
                className="relative z-10 leading-none"
                animate={{
                  color: isActive ? '#7B73FF' : 'rgba(255,255,255,0.32)',
                  y: isActive ? -1 : 0,
                }}
                transition={{ duration: 0.15 }}
              >
                <tab.Icon active={isActive} />
              </motion.span>

              <motion.span
                className="relative z-10 font-semibold leading-none"
                style={{ fontSize: 10 }}
                animate={{ color: isActive ? '#7B73FF' : 'rgba(255,255,255,0.28)' }}
                transition={{ duration: 0.15 }}
              >
                {tab.label}
              </motion.span>
            </motion.button>
          )
        })}
      </div>
    </nav>
  )
}
