/**
 * PayoutsPage — запросы выплат для Funded трейдеров.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { payoutsApi, type Payout } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import { BottomSheet } from '@/components/ui/BottomSheet'
import { CardSkeleton } from '@/components/ui/LoadingSkeleton'

const NETWORKS = [
  { id: 'TRC20', label: 'TRC20 (TRON)', fee: '~1 USDT', icon: '🔴' },
  { id: 'ERC20', label: 'ERC20 (Ethereum)', fee: '~5 USDT', icon: '🔵' },
  { id: 'BEP20', label: 'BEP20 (BSC)', fee: '~0.5 USDT', icon: '🟡' },
]

export function PayoutsPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [requestSheet, setRequestSheet] = useState(false)
  const [amount, setAmount] = useState('')
  const [network, setNetwork] = useState('TRC20')
  const [address, setAddress] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const { data: available, isLoading: availLoading } = useQuery({
    queryKey: ['payout-available', activeChallengeId],
    queryFn: () => payoutsApi.getAvailable(activeChallengeId!),
    enabled: !!activeChallengeId,
  })

  const { data: payouts = [], isLoading: payoutsLoading } = useQuery({
    queryKey: ['payouts', activeChallengeId],
    queryFn: () => payoutsApi.getList(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 30_000,
  })

  const requestMutation = useMutation({
    mutationFn: () =>
      payoutsApi.request({
        challenge_id: activeChallengeId!,
        amount: parseFloat(amount),
        network,
        wallet_address: address,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payouts'] })
      queryClient.invalidateQueries({ queryKey: ['payout-available'] })
      setRequestSheet(false)
      setAmount('')
      setAddress('')
      setSuccessMsg('Запрос на выплату отправлен!')
      setTimeout(() => setSuccessMsg(''), 4000)
    },
  })

  const canRequest =
    amount &&
    address &&
    parseFloat(amount) > 0 &&
    parseFloat(amount) <= (available?.available_amount ?? 0)

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <span className="text-5xl">💰</span>
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">Только Funded трейдеры могут запрашивать выплаты</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white text-xl font-bold"
          style={{ background: 'rgba(255,255,255,0.08)' }}
        >
          ‹
        </button>
        <h1 className="text-xl font-bold text-white">Выплаты</h1>
      </div>

      {/* Success message */}
      {successMsg && (
        <motion.div
          className="mx-4 mb-3 p-3 rounded-xl text-center text-sm font-semibold text-profit"
          style={{ background: 'rgba(0,212,170,0.1)', border: '1px solid rgba(0,212,170,0.2)' }}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
        >
          ✓ {successMsg}
        </motion.div>
      )}

      {/* Available balance card */}
      <div className="mx-4 mb-4">
        {availLoading ? (
          <CardSkeleton />
        ) : (
          <div
            className="glass-card p-5 relative overflow-hidden"
          >
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'radial-gradient(circle at 100% 0%, rgba(0,212,170,0.08) 0%, transparent 60%)',
              }}
            />
            <p className="text-text-secondary text-xs mb-1">Доступно к выводу</p>
            <p className="num text-3xl font-bold text-white mb-1">
              ${(available?.available_amount ?? 0).toLocaleString('en', { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-text-muted">
              Минимум: ${available?.min_payout ?? 100} ·{' '}
              Сплит: {available?.profit_split_pct ?? 80}% трейдеру
            </p>
            {(available?.available_amount ?? 0) >= (available?.min_payout ?? 100) ? (
              <motion.button
                className="mt-4 w-full py-3 rounded-xl font-bold text-white text-sm"
                style={{
                  background: 'linear-gradient(135deg, #00D4AA, #00B894)',
                  boxShadow: '0 4px 20px rgba(0,212,170,0.3)',
                }}
                onClick={() => setRequestSheet(true)}
                whileTap={{ scale: 0.97 }}
              >
                💰 Запросить выплату
              </motion.button>
            ) : (
              <p className="mt-3 text-center text-xs text-text-muted">
                Минимальная сумма для вывода: ${available?.min_payout ?? 100}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Info blocks */}
      <div className="mx-4 mb-4 grid grid-cols-2 gap-3">
        <div className="glass-card p-3 text-center">
          <p className="text-xs text-text-secondary">Выплачено</p>
          <p className="num text-lg font-bold text-white mt-1">
            ${(available?.total_paid ?? 0).toFixed(0)}
          </p>
        </div>
        <div className="glass-card p-3 text-center">
          <p className="text-xs text-text-secondary">Выплат</p>
          <p className="num text-lg font-bold text-white mt-1">{payouts.length}</p>
        </div>
      </div>

      {/* Payout history */}
      <div className="px-4">
        <p className="text-xs text-text-secondary uppercase tracking-wider mb-3">
          История выплат
        </p>
        {payoutsLoading ? (
          <CardSkeleton />
        ) : payouts.length === 0 ? (
          <p className="text-center text-text-muted text-sm py-8">Выплат пока нет</p>
        ) : (
          <div className="space-y-2">
            {payouts.map((payout) => (
              <PayoutRow key={payout.payout_id} payout={payout} />
            ))}
          </div>
        )}
      </div>

      {/* Request payout bottom sheet */}
      <BottomSheet
        isOpen={requestSheet}
        onClose={() => setRequestSheet(false)}
        title="Запрос выплаты"
        height="80vh"
      >
        <div className="px-5 py-4 space-y-4">
          {/* Amount */}
          <div className="space-y-1">
            <label className="text-xs text-text-secondary">Сумма (USDT)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={`Макс. ${(available?.available_amount ?? 0).toFixed(2)}`}
              className="w-full bg-bg-border border border-bg-border rounded-xl px-3 py-3 text-white text-base num focus:outline-none focus:border-brand-primary/50"
              inputMode="decimal"
            />
            {amount && parseFloat(amount) > (available?.available_amount ?? 0) && (
              <p className="text-loss text-xs">Недостаточно средств</p>
            )}
          </div>

          {/* Quick amounts */}
          <div className="flex gap-2">
            {[25, 50, 100].map((pct) => {
              const amt = ((available?.available_amount ?? 0) * pct) / 100
              return (
                <button
                  key={pct}
                  className="flex-1 py-2 rounded-lg text-xs font-semibold"
                  style={{ background: '#1E1E2E', color: '#4A4A5A' }}
                  onClick={() => setAmount(amt.toFixed(2))}
                >
                  {pct}%
                </button>
              )
            })}
            <button
              className="flex-1 py-2 rounded-lg text-xs font-semibold"
              style={{ background: '#1E1E2E', color: '#4A4A5A' }}
              onClick={() => setAmount((available?.available_amount ?? 0).toFixed(2))}
            >
              Макс
            </button>
          </div>

          {/* Network */}
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Сеть</label>
            {NETWORKS.map((n) => (
              <button
                key={n.id}
                className="w-full p-3 rounded-xl flex items-center justify-between transition-all"
                style={{
                  background: network === n.id ? 'rgba(108,99,255,0.15)' : '#1E1E2E',
                  border: network === n.id ? '1px solid rgba(108,99,255,0.4)' : '1px solid transparent',
                }}
                onClick={() => setNetwork(n.id)}
              >
                <div className="flex items-center gap-2">
                  <span>{n.icon}</span>
                  <span className="text-sm text-white">{n.label}</span>
                </div>
                <span className="text-xs text-text-muted">{n.fee}</span>
              </button>
            ))}
          </div>

          {/* Wallet address */}
          <div className="space-y-1">
            <label className="text-xs text-text-secondary">Адрес кошелька</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Вставь адрес USDT кошелька"
              className="w-full bg-bg-border border border-bg-border rounded-xl px-3 py-3 text-white text-xs focus:outline-none focus:border-brand-primary/50"
            />
          </div>

          {/* Summary */}
          {amount && address && parseFloat(amount) > 0 && (
            <div className="p-3 rounded-xl space-y-2" style={{ background: '#1E1E2E' }}>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Сумма запроса</span>
                <span className="num font-bold text-white">${parseFloat(amount).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Платформе ({100 - (available?.profit_split_pct ?? 80)}%)</span>
                <span className="num text-text-muted">
                  -${(parseFloat(amount) * (1 - (available?.profit_split_pct ?? 80) / 100)).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-sm border-t border-bg-border pt-2">
                <span className="text-text-secondary">Вы получите</span>
                <span className="num font-bold text-profit">
                  ${(parseFloat(amount) * (available?.profit_split_pct ?? 80) / 100).toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {requestMutation.isError && (
            <p className="text-loss text-xs text-center">
              Ошибка при отправке запроса. Попробуйте снова.
            </p>
          )}

          <motion.button
            className="w-full py-4 rounded-2xl font-bold text-white"
            style={{
              background: canRequest
                ? 'linear-gradient(135deg, #00D4AA, #00B894)'
                : '#1E1E2E',
              color: canRequest ? '#fff' : '#4A4A5A',
            }}
            onClick={() => canRequest && requestMutation.mutate()}
            disabled={!canRequest || requestMutation.isPending}
            whileTap={canRequest ? { scale: 0.97 } : undefined}
          >
            {requestMutation.isPending ? '⏳ Отправка...' : '💰 Подтвердить запрос'}
          </motion.button>
        </div>
      </BottomSheet>
    </div>
  )
}

function PayoutRow({ payout }: { payout: Payout }) {
  const statusConfig = {
    pending: { label: 'На проверке', color: '#FFA502', bg: 'rgba(255,165,2,0.1)' },
    approved: { label: 'Одобрено', color: '#00D4AA', bg: 'rgba(0,212,170,0.1)' },
    rejected: { label: 'Отклонено', color: '#FF4757', bg: 'rgba(255,71,87,0.1)' },
    sent: { label: 'Отправлено', color: '#00D4AA', bg: 'rgba(0,212,170,0.1)' },
  }
  const status = statusConfig[payout.status as keyof typeof statusConfig] ?? statusConfig.pending
  const date = new Date(payout.created_at)

  return (
    <div className="glass-card p-3 flex items-center justify-between">
      <div>
        <p className="num text-sm font-bold text-white">${payout.amount.toFixed(2)}</p>
        <p className="text-xs text-text-muted mt-0.5">
          {payout.network} · {date.toLocaleDateString('ru', { day: '2-digit', month: 'short' })}
        </p>
      </div>
      <span
        className="text-xs font-semibold px-2 py-1 rounded-lg"
        style={{ background: status.bg, color: status.color }}
      >
        {status.label}
      </span>
    </div>
  )
}
