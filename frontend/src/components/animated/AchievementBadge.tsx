/**
 * AchievementBadge — бейдж достижения с уровнями и анимацией разблокировки.
 */
import { motion } from 'framer-motion'
import { AnimatedIcon } from './AnimatedIcon'

type BadgeLevel = 'locked' | 'bronze' | 'silver' | 'gold' | 'platinum'

const LEVEL_COLORS: Record<BadgeLevel, string> = {
  locked: '#2A2A3A',
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  platinum: '#E5E4E2',
}

const LEVEL_GLOW: Record<BadgeLevel, string> = {
  locked: 'transparent',
  bronze: 'rgba(205, 127, 50, 0.4)',
  silver: 'rgba(192, 192, 192, 0.4)',
  gold: 'rgba(255, 215, 0, 0.5)',
  platinum: 'rgba(229, 228, 226, 0.6)',
}

interface AchievementBadgeProps {
  name: string
  lottieSrc?: string
  level: string
  progress: number
  maxProgress?: number
  isNew?: boolean
  size?: number
  onClick?: () => void
}

export function AchievementBadge({
  name,
  lottieSrc,
  level,
  progress,
  maxProgress = 100,
  isNew = false,
  size = 72,
  onClick,
}: AchievementBadgeProps) {
  const lvl = level as BadgeLevel
  const isLocked = lvl === 'locked'
  const color = LEVEL_COLORS[lvl]
  const glow = LEVEL_GLOW[lvl]

  return (
    <motion.div
      className="flex flex-col items-center gap-2 cursor-pointer"
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
    >
      <div className="relative">
        {/* Badge ring */}
        <motion.div
          className="rounded-2xl flex items-center justify-center"
          style={{
            width: size,
            height: size,
            background: isLocked
              ? 'rgba(30, 30, 46, 0.8)'
              : `linear-gradient(135deg, ${color}20, ${color}08)`,
            border: `2px solid ${color}`,
            boxShadow: isLocked ? 'none' : `0 0 16px ${glow}`,
          }}
          animate={isNew ? {
            boxShadow: [`0 0 16px ${glow}`, `0 0 32px ${glow}`, `0 0 16px ${glow}`],
          } : {}}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          {lottieSrc && !isLocked ? (
            <AnimatedIcon
              src={lottieSrc}
              size={size * 0.6}
              staticSrc={lottieSrc.replace('.lottie', '.png')}
            />
          ) : (
            <span style={{ fontSize: size * 0.35, filter: isLocked ? 'grayscale(1) opacity(0.3)' : 'none' }}>
              🏅
            </span>
          )}

          {/* Lock icon */}
          {isLocked && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-text-muted" style={{ fontSize: size * 0.3 }}>🔒</span>
            </div>
          )}
        </motion.div>

        {/* Level indicator */}
        {!isLocked && (
          <div
            className="absolute -bottom-1 -right-1 rounded-full flex items-center justify-center text-xs font-bold"
            style={{
              width: 20,
              height: 20,
              background: color,
              color: '#0A0A0F',
              fontSize: 8,
              border: '2px solid #0A0A0F',
            }}
          >
            {lvl[0].toUpperCase()}
          </div>
        )}

        {/* New badge pulse */}
        {isNew && (
          <motion.div
            className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-brand-primary"
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        )}
      </div>

      {/* Name */}
      <span
        className="text-xs text-center leading-tight max-w-16"
        style={{ color: isLocked ? '#4A4A5A' : '#FFFFFF' }}
      >
        {name}
      </span>

      {/* Progress bar */}
      {isLocked && maxProgress > 0 && (
        <div className="w-full h-1 bg-bg-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-primary"
            style={{ width: `${Math.min(100, (progress / maxProgress) * 100)}%` }}
          />
        </div>
      )}
    </motion.div>
  )
}
