/**
 * StatusOverlay — полноэкранный видео-оверлей для событий:
 * funded_success, challenge_failed, scaling_up, payout_sent.
 */
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useRef } from 'react'

export type StatusType = 'funded_success' | 'challenge_failed' | 'scaling_up' | 'payout_sent'

const STATUS_CONFIG: Record<StatusType, { title: string; subtitle: string; color: string }> = {
  funded_success: {
    title: '💎 Финансирование получено!',
    subtitle: 'Ты стал Funded Trader',
    color: '#00D4AA',
  },
  challenge_failed: {
    title: '❌ Испытание провалено',
    subtitle: 'Не останавливайся — попробуй снова',
    color: '#FF4757',
  },
  scaling_up: {
    title: '📈 Счёт увеличен!',
    subtitle: 'Отличные результаты',
    color: '#6C63FF',
  },
  payout_sent: {
    title: '💰 Выплата отправлена!',
    subtitle: 'Средства на пути к тебе',
    color: '#FFA502',
  },
}

interface StatusOverlayProps {
  type: StatusType | null
  onComplete?: () => void
}

export function StatusOverlay({ type, onComplete }: StatusOverlayProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (!type || !videoRef.current) return
    videoRef.current.currentTime = 0
    videoRef.current.play().catch(() => {})

    const timer = setTimeout(() => {
      onComplete?.()
    }, 4000)
    return () => clearTimeout(timer)
  }, [type, onComplete])

  const config = type ? STATUS_CONFIG[type] : null

  return (
    <AnimatePresence>
      {type && config && (
        <motion.div
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.92)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          onClick={onComplete}
        >
          {/* Video background */}
          <video
            ref={videoRef}
            src={`/assets/status/${type}.mp4`}
            muted
            playsInline
            className="absolute inset-0 w-full h-full object-cover opacity-30"
            onError={() => {}}
          />

          {/* Content */}
          <motion.div
            className="relative z-10 text-center px-8"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          >
            <motion.div
              className="text-6xl mb-6"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              {type === 'funded_success' ? '💎' :
               type === 'challenge_failed' ? '❌' :
               type === 'scaling_up' ? '📈' : '💰'}
            </motion.div>
            <h2
              className="text-3xl font-bold mb-2"
              style={{ color: config.color, textShadow: `0 0 30px ${config.color}60` }}
            >
              {config.title}
            </h2>
            <p className="text-text-secondary text-lg">{config.subtitle}</p>
            <p className="text-text-muted text-sm mt-6">Нажмите, чтобы продолжить</p>
          </motion.div>

          {/* Glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: `radial-gradient(circle at center, ${config.color}15 0%, transparent 70%)`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
