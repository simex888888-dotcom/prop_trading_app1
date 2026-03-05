/**
 * DashboardPage — главный дашборд CHM_KRYPTON.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { statsApi, challengesApi } from '@/api/client'
import { PnLNumber } from '@/components/ui/PnLNumber'
import { RiskMeter } from '@/components/ui/RiskMeter'
import { DashboardSkeleton } from '@/components/ui/LoadingSkeleton'
import { BottomSheet } from '@/components/ui/BottomSheet'
import { EquitySparkline } from '@/components/charts/EquitySparkline'
import { AnimatedRank, getRankByStats } from '@/components/animated/AnimatedRank'
import { useAppStore } from '@/store/appStore'

function ModeBadge({ mode, hasChallengeActive }: { mode?: string; hasChallengeActive?: boolean }) {
  const isFunded = mode === 'funded'
  const isChallenge = mode === 'demo' && hasChallengeActive

  const bg = isFunded
    ? 'rgba(0,212,170,0.15)'
    : isChallenge
    ? 'rgba(108,99,255,0.15)'
    : 'rgba(255,165,2,0.15)'
  const color = isFunded ? '#00D4AA' : isChallenge ? '#6C63FF' : '#FFA502'
  const border = isFunded
    ? 'rgba(0,212,170,0.3)'
    : isChallenge
    ? 'rgba(108,99,255,0.3)'
    : 'rgba(255,165,2,0.3)'
  const label = isFunded ? '● FUNDED' : isChallenge ? '● ИСПЫТАНИЕ' : '● DEMO'

  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full font-bold"
      style={{ background: bg, color, border: `1px solid ${border}` }}
    >
      {label}
    </span>
  )
}

function ProgressBar({ value, max = 100, color = '#6C63FF', label }: {
  value: number; max?: number; color?: string; label?: string
}) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex justify-between text-xs text-text-secondary">
          <span>{label}</span>
          <span className="num">{pct.toFixed(0)}%</span>
        </div>
      )}
      <div className="h-1.5 bg-bg-border rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const [showAccountDetails, setShowAccountDetails] = useState(false)
  const [accountDetails, setAccountDetails] = useState<{ bybit_uid: string; username: string; api_key: string; account_mode: string } | null>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  async function handleShowAccountDetails() {
    if (!activeChallengeId) return
    setLoadingDetails(true)
    try {
      const details = await challengesApi.getAccountDetails(activeChallengeId)
      setAccountDetails(details)
      setShowAccountDetails(true)
    } catch (e) {
      // silently ignore — user will see empty state
      setShowAccountDetails(true)
    } finally {
      setLoadingDetails(false)
    }
  }

  function copyToClipboard(text: string, field: string) {
    navigator.clipboard?.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', activeChallengeId],
    queryFn: () => statsApi.getDashboard(activeChallengeId ?? undefined),
    refetchInterval: 10_000,
  })

  const { data: equityCurve = [] } = useQuery({
    queryKey: ['equity-curve', activeChallengeId],
    queryFn: () => statsApi.getEquityCurve(activeChallengeId!),
    enabled: !!activeChallengeId,
  })

  if (isLoading) return <DashboardSkeleton />

  const d = dashboard
  const rank = getRankByStats(
    d?.account_mode === 'funded' ? 1 : 0,
    d?.total_pnl ?? 0
  )

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.07 } },
  }
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }

  return (
    <motion.div
      className="flex flex-col gap-4 px-4 pt-4 pb-24"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">CHM KRYPTON</h1>
          <p className="text-text-secondary text-xs">Trade Like an Element</p>
        </div>
        <div className="flex items-center gap-3">
          <AnimatedRank rank={rank} size={44} showLabel={false} />
          <ModeBadge mode={d?.account_mode} hasChallengeActive={!!d?.active_challenge_id} />
        </div>
      </motion.div>

      {/* Main account card */}
      <motion.div variants={item} className="glass-card p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-text-secondary text-xs mb-1">Equity</p>
            <PnLNumber
              value={d?.equity ?? 0}
              showSign={false}
              size="xl"
              prefix="$"
            />
          </div>
          {d?.active_challenge_id && (
            <div className="text-right">
              <p className="text-text-secondary text-xs mb-1">Дн. PnL</p>
              <PnLNumber value={d?.daily_pnl ?? 0} size="lg" />
            </div>
          )}
        </div>

        {/* Equity sparkline */}
        {equityCurve.length > 0 && (
          <EquitySparkline data={equityCurve} height={64} />
        )}

        {/* Profit progress */}
        {d?.active_challenge_id && (
          <ProgressBar
            value={d.profit_progress_pct}
            label={`Цель: ${d.profit_target_pct}%`}
            color={d.profit_progress_pct >= 100 ? '#00D4AA' : '#6C63FF'}
          />
        )}
      </motion.div>

      {/* Risk indicators */}
      {d?.active_challenge_id && (
        <motion.div variants={item} className="glass-card p-4">
          <p className="text-text-secondary text-xs mb-3">Лимиты риска</p>
          <div className="flex items-center justify-around">
            <div className="flex flex-col items-center gap-1">
              <RiskMeter value={d.daily_dd_pct / d.daily_dd_limit * 100} size={72} label="Дневная" />
              <span className="text-xs text-text-muted">
                {d.daily_dd_pct.toFixed(1)}% / {d.daily_dd_limit}%
              </span>
            </div>
            <div className="w-px h-16 bg-bg-border" />
            <div className="flex flex-col items-center gap-1">
              <RiskMeter value={d.total_dd_pct / d.daily_dd_limit * 100} size={72} label="Общая" />
              <span className="text-xs text-text-muted">
                {d.total_dd_pct.toFixed(1)}% / {d.daily_dd_limit}%
              </span>
            </div>
            <div className="w-px h-16 bg-bg-border" />
            <div className="flex flex-col items-center gap-2">
              <div className="num text-2xl font-bold text-white">
                {d.trading_days_count}
                <span className="text-text-muted text-sm">/{d.min_trading_days}</span>
              </div>
              <span className="text-xs text-text-secondary">Торг. дней</span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Streak */}
      <motion.div variants={item} className="glass-card p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.div
            animate={{ scale: [1, 1.15, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-2xl"
          >
            🔥
          </motion.div>
          <div>
            <p className="text-white font-semibold">Streak без нарушений</p>
            <p className="text-text-muted text-xs">Удерживай серию</p>
          </div>
        </div>
        <span className="num text-3xl font-bold text-profit">
          {d?.streak_days ?? 0}
        </span>
      </motion.div>

      {/* Quick actions */}
      <motion.div variants={item} className="grid grid-cols-2 gap-3">
        <QuickAction icon="⚡" label="Торговать" onClick={() => navigate('/terminal')} color="#6C63FF" />
        <QuickAction icon="📋" label="Правила" onClick={() => navigate('/rules')} color="#00D4AA" />
        <QuickAction icon="💰" label="Выплаты" onClick={() => navigate('/payouts')} color="#FFA502" />
        <QuickAction icon="🏆" label="Рейтинг" onClick={() => navigate('/profile')} color="#FFD700" />
        {d?.active_challenge_id && (
          <QuickAction
            icon={loadingDetails ? '⏳' : '🔑'}
            label="Bybit аккаунт"
            onClick={handleShowAccountDetails}
            color="#00B8FF"
          />
        )}
      </motion.div>

      {/* No active challenge */}
      {!d?.active_challenge_id && (
        <motion.div
          variants={item}
          className="glass-card p-6 text-center space-y-3"
        >
          <div className="text-4xl">⚛️</div>
          <p className="text-white font-semibold">Начни своё испытание</p>
          <p className="text-text-secondary text-sm">
            Выбери размер счёта и начни путь трейдера
          </p>
          <motion.button
            className="w-full py-3 rounded-xl font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
            onClick={() => navigate('/challenges')}
            whileTap={{ scale: 0.97 }}
          >
            Выбрать испытание
          </motion.button>
        </motion.div>
      )}

      {/* Account details bottom sheet */}
      <BottomSheet
        isOpen={showAccountDetails}
        onClose={() => setShowAccountDetails(false)}
        title="Bybit субаккаунт"
      >
        <div className="p-5 space-y-4">
          {accountDetails ? (
            <>
              <p className="text-text-secondary text-sm text-center">
                Эти данные — ваш Bybit субаккаунт для торговли.
                Вы можете торговать прямо в приложении или подключить аккаунт в Bybit по API ключу.
              </p>

              {/* Trade in app */}
              <motion.button
                className="w-full py-4 rounded-2xl font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
                onClick={() => { setShowAccountDetails(false); navigate('/terminal') }}
                whileTap={{ scale: 0.97 }}
              >
                ⚡ Торговать в приложении
              </motion.button>

              <div className="relative flex items-center">
                <div className="flex-1 border-t border-bg-border" />
                <span className="px-3 text-xs text-text-muted">или используйте API</span>
                <div className="flex-1 border-t border-bg-border" />
              </div>

              {/* Credentials */}
              {[
                { label: 'Bybit UID', value: accountDetails.bybit_uid, field: 'uid' },
                { label: 'Sub-account username', value: accountDetails.username || '—', field: 'username' },
                { label: 'API Key', value: accountDetails.api_key || '—', field: 'api_key' },
              ].map(({ label, value, field }) => (
                <div key={field}
                  className="glass-card p-3 space-y-1"
                  style={{ border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <p className="text-xs text-text-muted">{label}</p>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-white font-mono break-all">{value}</span>
                    {value !== '—' && (
                      <button
                        onClick={() => copyToClipboard(value, field)}
                        className="shrink-0 text-xs px-2 py-1 rounded-lg font-semibold transition-all"
                        style={{
                          background: copiedField === field ? 'rgba(0,212,170,0.2)' : 'rgba(108,99,255,0.2)',
                          color: copiedField === field ? '#00D4AA' : '#a89fff',
                        }}
                      >
                        {copiedField === field ? '✓' : 'Копировать'}
                      </button>
                    )}
                  </div>
                </div>
              ))}

              <p className="text-xs text-text-muted text-center">
                ⚠️ API Secret доступен только в момент создания субаккаунта. Торговля через приложение не требует API ключей.
              </p>
            </>
          ) : (
            <div className="text-center py-8">
              <p className="text-text-secondary">Нет данных о субаккаунте</p>
              <p className="text-xs text-text-muted mt-2">
                Возможно, аккаунт был создан вручную администратором
              </p>
              <motion.button
                className="mt-4 w-full py-4 rounded-2xl font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
                onClick={() => { setShowAccountDetails(false); navigate('/terminal') }}
                whileTap={{ scale: 0.97 }}
              >
                ⚡ Торговать в приложении
              </motion.button>
            </div>
          )}
        </div>
      </BottomSheet>
    </motion.div>
  )
}

function QuickAction({ icon, label, onClick, color }: {
  icon: string; label: string; onClick: () => void; color: string
}) {
  return (
    <motion.button
      className="glass-card p-4 flex items-center gap-3"
      onClick={onClick}
      whileTap={{ scale: 0.95 }}
    >
      <span
        className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}
      >
        {icon}
      </span>
      <span className="font-semibold text-sm text-white">{label}</span>
    </motion.button>
  )
}
