/**
 * AnimatedTabBar — нижняя навигационная панель.
 */
import { motion } from 'framer-motion'
import { useLocation, useNavigate } from 'react-router-dom'

interface Tab {
  path: string
  icon: string
  label: string
}

const TABS: Tab[] = [
  { path: '/dashboard', icon: '📊', label: 'Главная' },
  { path: '/terminal', icon: '⚡', label: 'Торговля' },
  { path: '/challenges', icon: '🎯', label: 'Испытания' },
  { path: '/history', icon: '📈', label: 'История' },
  { path: '/profile', icon: '👤', label: 'Профиль' },
]

export function AnimatedTabBar() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 tab-bar">
      <div
        className="flex items-center justify-around px-2 pt-2 pb-1"
        style={{
          background: 'rgba(18, 18, 26, 0.95)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderTop: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {TABS.map((tab) => {
          const isActive = location.pathname.startsWith(tab.path)
          return (
            <motion.button
              key={tab.path}
              className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl min-w-0"
              onClick={() => navigate(tab.path)}
              whileTap={{ scale: 0.9 }}
              animate={isActive ? { y: -2 } : { y: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            >
              <motion.span
                className="text-xl"
                animate={isActive ? { scale: 1.15 } : { scale: 1 }}
                transition={{ type: 'spring', stiffness: 300 }}
                style={{ filter: isActive ? 'none' : 'grayscale(0.5) opacity(0.6)' }}
              >
                {tab.icon}
              </motion.span>
              <motion.span
                className="text-[10px] font-medium truncate"
                animate={{ color: isActive ? '#6C63FF' : '#4A4A5A' }}
                transition={{ duration: 0.2 }}
              >
                {tab.label}
              </motion.span>
              {isActive && (
                <motion.div
                  className="absolute bottom-1 w-1 h-1 rounded-full bg-brand-primary"
                  layoutId="tab-indicator"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
            </motion.button>
          )
        })}
      </div>
    </nav>
  )
}
