/**
 * DashboardPage — главный дашборд CHM_KRYPTON.
 */
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { statsApi, tradingApi, challengesApi, type BybitCredentials } from '@/api/client'
import { PnLNumber } from '@/components/ui/PnLNumber'
import { RiskMeter } from '@/components/ui/RiskMeter'
import { DashboardSkeleton } from '@/components/ui/LoadingSkeleton'
import { EquitySparkline } from '@/components/charts/EquitySparkline'
import { AnimatedRank, getRankByStats } from '@/components/animated/AnimatedRank'
import { useAppStore } from '@/store/appStore'
import { BottomSheet } from '@/components/ui/BottomSheet'

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
  const setActiveChallenge = useAppStore((s) => s.setActiveChallenge)
  const [showBybitModal, setShowBybitModal] = useState(false)
  const [bybitCreds, setBybitCreds] = useState<BybitCredentials | null>(null)
  const [credsLoading, setCredsLoading] = useState(false)
  const [credsError, setCredsError] = useState(false)
  const [activating, setActivating] = useState(false)
  const [activateError, setActivateError] = useState('')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Auto-set active challenge on mount if not already set
  useEffect(() => {
    if (!activeChallengeId) {
      challengesApi.my().then((challenges) => {
        const active = challenges.find((c) =>
          ['phase1', 'phase2', 'funded'].includes(c.status)
        )
        if (active) setActiveChallenge(active)
      }).catch(() => {})
    }
  }, [])

  const copyToClipboard = (value: string, key: string) => {
    navigator.clipboard.writeText(value).then(() => {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    })
  }

  const openBybitCreds = async () => {
    if (!activeChallengeId) return
    setShowBybitModal(true)
    if (bybitCreds) return
    setCredsError(false)
    setCredsLoading(true)
    try {
      const creds = await challengesApi.getCredentials(activeChallengeId)
      setBybitCreds(creds)
    } catch {
      setCredsError(true)
    } finally {
      setCredsLoading(false)
    }
  }

  const selfActivate = async () => {
    if (!activeChallengeId) return
    setActivating(true)
    setActivateError('')
    try {
      await challengesApi.activateSelf(activeChallengeId)
      // Now fetch credentials
      const creds = await challengesApi.getCredentials(activeChallengeId)
      setBybitCreds(creds)
      setCredsError(false)
    } catch (e: any) {
      setActivateError(e?.response?.data?.detail ?? 'Не удалось активировать. Попробуйте ещё раз.')
    } finally {
      setActivating(false)
    }
  }

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', activeChallengeId],
    queryFn: () => statsApi.getDashboard(activeChallengeId ?? undefined),
    refetchInterval: 10_000,
  })

  // Живой баланс напрямую с Bybit (обновляется чаще, не из БД)
  const { data: liveBalance } = useQuery({
    queryKey: ['live-balance', activeChallengeId],
    queryFn: () => tradingApi.getBalance(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 8_000,
  })

  const { data: equityCurve = [] } = useQuery({
    queryKey: ['equity-curve', activeChallengeId],
    queryFn: () => statsApi.getEquityCurve(activeChallengeId!),
    enabled: !!activeChallengeId,
  })

  if (isLoading) return <DashboardSkeleton />

  const d = dashboard
  // Показываем живой equity из Bybit если доступен, иначе из БД
  const displayEquity = liveBalance?.equity ?? d?.equity ?? 0
  const displayUnrealizedPnl = liveBalance?.unrealized_pnl ?? 0
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

      {/* Main account card — выделенный баланс */}
      <motion.div variants={item} className="glass-card p-5 space-y-4"
        style={{ border: '1px solid rgba(108,99,255,0.25)', boxShadow: '0 4px 24px rgba(108,99,255,0.1)' }}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-text-secondary text-xs mb-1 uppercase tracking-wide">
              Equity {liveBalance ? '● Live' : ''}
            </p>
            {/* Большой яркий баланс */}
            <div className="flex items-baseline gap-2">
              <span className="num text-4xl font-black text-white">
                ${displayEquity.toLocaleString('en', { maximumFractionDigits: 2 })}
              </span>
            </div>
            {/* Нереализованный PnL */}
            {displayUnrealizedPnl !== 0 && (
              <div className={`flex items-center gap-1 mt-1 ${displayUnrealizedPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                <span className="text-sm">{displayUnrealizedPnl >= 0 ? '▲' : '▼'}</span>
                <span className="num text-sm font-semibold">
                  {displayUnrealizedPnl >= 0 ? '+' : ''}{displayUnrealizedPnl.toFixed(2)} unrealized
                </span>
              </div>
            )}
          </div>
          {d?.active_challenge_id && (
            <div className="text-right">
              <p className="text-text-secondary text-xs mb-1">Дн. PnL</p>
              <PnLNumber value={d?.daily_pnl ?? 0} size="lg" />
              <p className="text-text-secondary text-xs mt-2 mb-0.5">Total PnL</p>
              <PnLNumber value={d?.total_pnl ?? 0} size="sm" />
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
        <QuickAction icon="⚡" label="Терминал" onClick={() => navigate('/terminal')} color="#6C63FF" />
        <QuickAction icon="🔗" label="Bybit Demo" onClick={openBybitCreds} color="#FFA502" />
        <QuickAction icon="💰" label="Выплаты" onClick={() => navigate('/payouts')} color="#00D4AA" />
        <QuickAction icon="📋" label="Правила" onClick={() => navigate('/rules')} color="#888" />
      </motion.div>

      {/* Trading modal */}
      <BottomSheet
        isOpen={showBybitModal}
        onClose={() => setShowBybitModal(false)}
        title="Торговля в испытании"
        height="70vh"
      >
        <div className="px-5 pb-6 space-y-4">
          {credsLoading ? (
            <div className="flex items-center justify-center py-8 gap-3">
              <div className="w-5 h-5 rounded-full border-2 border-brand-primary border-t-transparent animate-spin" />
              <span className="text-text-secondary text-sm">Загрузка...</span>
            </div>
          ) : bybitCreds?.mode === 'bybit' ? (
            <>
              {([
                { label: 'API Key', value: bybitCreds.api_key, key: 'key' },
                { label: 'API Secret', value: bybitCreds.api_secret, key: 'secret' },
                { label: 'Sub UID', value: bybitCreds.sub_uid, key: 'uid' },
              ] as const).map(({ label, value, key }) => (
                <div key={key} className="space-y-1">
                  <p className="text-xs text-text-muted">{label}</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs text-white bg-bg-border rounded-xl px-3 py-2.5 truncate">
                      {value}
                    </code>
                    <button
                      className="shrink-0 px-3 py-2.5 rounded-xl text-xs font-bold transition-colors"
                      style={{
                        background: copiedKey === key ? 'rgba(0,212,170,0.2)' : 'rgba(108,99,255,0.2)',
                        color: copiedKey === key ? '#00D4AA' : '#6C63FF',
                      }}
                      onClick={() => copyToClipboard(value, key)}
                    >
                      {copiedKey === key ? '✓' : 'Копировать'}
                    </button>
                  </div>
                </div>
              ))}
              <div className="rounded-xl p-3 text-xs text-text-secondary space-y-1"
                style={{ background: 'rgba(255,165,2,0.07)', border: '1px solid rgba(255,165,2,0.2)' }}>
                <p className="font-semibold text-[#FFA502]">Как подключить Bybit:</p>
                <p>1. Перейди на <span className="text-profit font-medium">testnet.bybit.com</span></p>
                <p>2. Войди в аккаунт → API Management</p>
                <p>3. Создай подключение с API Key + Secret</p>
              </div>
            </>
          ) : bybitCreds?.mode === 'paper' ? (
            <div className="space-y-4 py-2">
              <div className="text-center space-y-3">
                <div className="text-5xl">📊</div>
                <p className="text-white font-bold text-lg">Paper Trading</p>
                <p className="text-text-secondary text-sm leading-relaxed">
                  Твоё испытание проходит во встроенном симуляторе с реальными ценами Bybit.
                  Торгуй через терминал приложения.
                </p>
              </div>
              <div className="rounded-xl p-3 text-xs text-text-secondary space-y-1.5"
                style={{ background: 'rgba(108,99,255,0.08)', border: '1px solid rgba(108,99,255,0.2)' }}>
                <p className="font-semibold text-[#6C63FF]">Как торговать:</p>
                <p>1. Открой терминал в приложении</p>
                <p>2. Выбери инструмент и направление</p>
                <p>3. Результаты учитываются в испытании</p>
              </div>
            </div>
          ) : credsError ? (
            <div className="space-y-4 py-2">
              <div className="text-center space-y-2">
                <div className="text-4xl">⚡</div>
                <p className="text-white font-semibold">Аккаунт не активирован</p>
                <p className="text-text-secondary text-sm">
                  Нажмите кнопку — испытание будет активировано в режиме Paper Trading
                </p>
              </div>

              <motion.button
                whileTap={{ scale: 0.97 }}
                className="w-full py-4 rounded-2xl font-bold text-white flex items-center justify-center gap-2"
                style={{ background: 'linear-gradient(135deg, #6C63FF, #5A52E0)' }}
                disabled={activating}
                onClick={selfActivate}
              >
                {activating ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Активируем...</span>
                  </>
                ) : (
                  <><span>⚡</span><span>Активировать испытание</span></>
                )}
              </motion.button>

              {activateError && (
                <p className="text-xs text-center px-2" style={{ color: '#FF4757' }}>
                  {activateError}
                </p>
              )}
            </div>
          ) : null}

          <motion.button
            whileTap={{ scale: 0.97 }}
            className="w-full py-3.5 rounded-2xl font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #6C63FF, #5A52E0)' }}
            onClick={() => { setShowBybitModal(false); navigate('/terminal') }}
          >
            ⚡ Открыть терминал
          </motion.button>
        </div>
      </BottomSheet>

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
