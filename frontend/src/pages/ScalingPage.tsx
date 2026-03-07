/**
 * ScalingPage — дорожная карта масштабирования счёта.
 */
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { challengesApi } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import { CardSkeleton } from '@/components/ui/LoadingSkeleton'
import { TrendUpIcon } from '@/components/ui/Icon'

const SCALING_STEPS = [
  { step: 1, label: 'Старт', multiplier: 1, profit_pct: 0, color: '#6C63FF' },
  { step: 2, label: 'Первый рост', multiplier: 1.25, profit_pct: 10, color: '#00D4AA' },
  { step: 3, label: 'Разгон', multiplier: 1.5625, profit_pct: 10, color: '#00D4AA' },
  { step: 4, label: 'Ускорение', multiplier: 1.953, profit_pct: 10, color: '#FFA502' },
  { step: 5, label: 'Элита', multiplier: 2.441, profit_pct: 10, color: '#FFA502' },
  { step: 6, label: 'Мастер', multiplier: 3.052, profit_pct: 10, color: '#FFD700' },
  { step: 7, label: 'Krypton', multiplier: 3.815, profit_pct: 10, color: '#FFD700' },
]

export function ScalingPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)

  const { data: challenge, isLoading } = useQuery({
    queryKey: ['challenge-detail', activeChallengeId],
    queryFn: () => challengesApi.getDetail(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 60_000,
  })

  const { data: rules } = useQuery({
    queryKey: ['challenge-rules', activeChallengeId],
    queryFn: () => challengesApi.getRules(activeChallengeId!),
    enabled: !!activeChallengeId,
  })

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <TrendUpIcon size={56} color="#6C63FF" />
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">Только Funded трейдеры могут масштабировать счёт</p>
      </div>
    )
  }

  const initialBalance = challenge?.challenge_type?.account_size ?? challenge?.initial_balance ?? 10000
  const currentBalance = challenge?.current_balance ?? initialBalance
  const scalingStep = challenge?.scaling_step ?? 0
  const totalPnlPct = rules?.current_profit_pct ?? 0

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <h1 className="text-xl font-bold text-white">Масштабирование</h1>
        <p className="text-text-secondary text-sm mt-0.5">Зарабатывай 10% — и мы увеличим счёт на 25%</p>
      </div>

      {/* Current account */}
      {isLoading ? (
        <div className="mx-4 mb-4"><CardSkeleton /></div>
      ) : (
        <div className="mx-4 mb-4 glass-card p-5 relative overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(circle at 0% 100%, rgba(108,99,255,0.1) 0%, transparent 60%)',
            }}
          />
          <div className="relative z-10">
            <p className="text-text-secondary text-xs mb-1">Текущий размер счёта</p>
            <p className="num text-3xl font-bold text-white">
              ${currentBalance.toLocaleString('en', { maximumFractionDigits: 0 })}
            </p>
            <div className="flex gap-4 mt-3">
              <div>
                <p className="text-xs text-text-muted">Начальный</p>
                <p className="num text-sm text-white">${initialBalance.toLocaleString('en')}</p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Шаг</p>
                <p className="num text-sm text-white">{scalingStep} / {SCALING_STEPS.length - 1}</p>
              </div>
              <div>
                <p className="text-xs text-text-muted">P&L</p>
                <p
                  className="num text-sm font-bold"
                  style={{ color: totalPnlPct >= 0 ? '#00D4AA' : '#FF4757' }}
                >
                  {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Next scaling target */}
      {scalingStep < SCALING_STEPS.length - 1 && (
        <div className="mx-4 mb-4 glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-white">До следующего масштабирования</p>
            <span className="num text-sm font-bold" style={{ color: '#FFA502' }}>
              {Math.max(0, 10 - (totalPnlPct % 10)).toFixed(2)}%
            </span>
          </div>
          <div className="h-2 bg-bg-border rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #6C63FF, #00D4AA)' }}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, (totalPnlPct % 10) * 10)}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
          <p className="text-xs text-text-muted mt-2">
            Новый размер счёта: $
            {(currentBalance * 1.25).toLocaleString('en', { maximumFractionDigits: 0 })}
          </p>
        </div>
      )}

      {/* Scaling roadmap */}
      <div className="px-4">
        <p className="text-xs text-text-secondary uppercase tracking-wider mb-3">
          Дорожная карта масштабирования
        </p>
        <div className="relative">
          {/* Vertical line */}
          <div
            className="absolute left-5 top-0 bottom-0 w-0.5"
            style={{ background: '#1E1E2E' }}
          />

          <div className="space-y-3">
            {SCALING_STEPS.map((step, i) => {
              const isCompleted = i < scalingStep
              const isCurrent = i === scalingStep
              const isLocked = i > scalingStep
              const accountAtStep = initialBalance * step.multiplier

              return (
                <motion.div
                  key={step.step}
                  className="flex items-start gap-4"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  {/* Step indicator */}
                  <div className="relative z-10 shrink-0">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2"
                      style={{
                        background: isCompleted ? step.color
                          : isCurrent ? `${step.color}20`
                          : '#0A0A0F',
                        borderColor: isCompleted || isCurrent ? step.color : '#1E1E2E',
                        color: isCompleted ? '#fff'
                          : isCurrent ? step.color
                          : '#4A4A5A',
                        boxShadow: isCurrent ? `0 0 20px ${step.color}40` : 'none',
                      }}
                    >
                      {isCompleted ? '✓' : step.step}
                    </div>
                  </div>

                  {/* Step content */}
                  <div
                    className="flex-1 rounded-2xl p-3 mb-1"
                    style={{
                      background: isCurrent ? `${step.color}10` : '#12121A',
                      border: isCurrent ? `1px solid ${step.color}30` : '1px solid #1E1E2E',
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p
                        className="text-sm font-bold"
                        style={{ color: isLocked ? '#4A4A5A' : step.color }}
                      >
                        {step.label}
                      </p>
                      <p
                        className="num text-sm font-bold"
                        style={{ color: isLocked ? '#4A4A5A' : '#fff' }}
                      >
                        ${accountAtStep.toLocaleString('en', { maximumFractionDigits: 0 })}
                      </p>
                    </div>
                    <p className="text-xs text-text-muted">
                      {i === 0 ? 'Стартовый счёт'
                        : `Заработай ${step.profit_pct}% → счёт ×1.25`}
                    </p>
                    {isCurrent && (
                      <div className="flex items-center gap-1 mt-2">
                        <div
                          className="w-2 h-2 rounded-full animate-pulse"
                          style={{ background: step.color }}
                        />
                        <span className="text-xs font-semibold" style={{ color: step.color }}>
                          Текущий уровень
                        </span>
                      </div>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Max account notice */}
      <div className="mx-4 mt-4 p-3 rounded-xl text-center" style={{ background: '#1E1E2E' }}>
        <p className="text-xs text-text-muted">
          Максимальный размер счёта: $2,000,000
        </p>
      </div>
    </div>
  )
}
