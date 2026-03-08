/**
 * ChallengesPage — выбор и покупка испытания.
 * После оплаты план становится pending_payment — активируется только после подтверждения администратором.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { challengesApi, type ChallengeType } from '@/api/client'
import { ChallengeCard } from '@/components/ui/ChallengeCard'
import { BottomSheet } from '@/components/ui/BottomSheet'
import { CardSkeleton } from '@/components/ui/LoadingSkeleton'
import { useAppStore } from '@/store/appStore'
import { useNavigate } from 'react-router-dom'
import { ClockIcon, CreditCardIcon, ClipboardIcon, AnimatedCheckIcon, SpinnerIcon } from '@/components/ui/Icon'

export function ChallengesPage() {
  const [selected, setSelected] = useState<ChallengeType | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [purchaseError, setPurchaseError] = useState('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const setActiveChallenge = useAppStore((s) => s.setActiveChallenge)

  const { data: types = [], isLoading } = useQuery({
    queryKey: ['challenge-types'],
    queryFn: challengesApi.list,
  })

  const { data: myChallenges = [] } = useQuery({
    queryKey: ['my-challenges'],
    queryFn: () => challengesApi.my(),
  })

  const purchaseMutation = useMutation({
    mutationFn: (id: number) => challengesApi.purchase(id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['my-challenges'] })
      setPurchaseError('')
      setShowConfirm(false)
      setShowSuccess(true)
      // Auto-set active challenge if status is active
      if (result && ['phase1', 'phase2', 'funded'].includes(result.status)) {
        setActiveChallenge(result)
      }
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ??
        err?.message ??
        'Ошибка при создании заявки. Попробуйте позже.'
      setPurchaseError(String(msg))
    },
  })

  const activeChallenge = myChallenges.find(
    (c) => c.status === 'phase1' || c.status === 'phase2' || c.status === 'funded'
  )
  const pendingChallenge = myChallenges.find((c) => c.status === 'pending_payment')
  const botUsername = (import.meta.env.VITE_BOT_USERNAME as string) || 'chm_prop_bot'

  return (
    <div className="flex flex-col gap-4 pt-4 pb-24">
      {/* Header */}
      <div className="px-4">
        <h1 className="text-xl font-bold text-white">Выбери путь</h1>
        <p className="text-text-secondary text-sm mt-1">
          Каждый план — уникальный маршрут к финансированию
        </p>
      </div>

      {/* Active challenge banner */}
      {activeChallenge && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-4 glass-card p-4 flex items-center justify-between"
          style={{ border: '1px solid rgba(0,212,170,0.3)' }}
        >
          <div>
            <p className="text-xs text-text-secondary">Активное испытание</p>
            <p className="font-semibold text-profit">
              Счёт #{activeChallenge.id} · {activeChallenge.status.toUpperCase()}
            </p>
          </div>
          <motion.button
            className="px-4 py-2 rounded-xl text-sm font-semibold text-profit"
            style={{ background: 'rgba(0,212,170,0.1)', border: '1px solid rgba(0,212,170,0.2)' }}
            onClick={() => navigate('/dashboard')}
            whileTap={{ scale: 0.95 }}
          >
            Перейти
          </motion.button>
        </motion.div>
      )}

      {/* Pending payment banner */}
      {pendingChallenge && !activeChallenge && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-4 glass-card p-4 space-y-1"
          style={{ border: '1px solid rgba(255,180,0,0.35)', background: 'rgba(255,180,0,0.05)' }}
        >
          <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: '#FFB400' }}>
            <ClockIcon size={12} color="#FFB400" />
            Ожидание подтверждения оплаты
          </p>
          <p className="text-sm text-text-secondary">
            Заявка #{pendingChallenge.id} на рассмотрении.{' '}
            Отправьте скриншот оплаты боту{' '}
            <span className="text-white font-semibold">@{botUsername}</span>.
          </p>
        </motion.div>
      )}

      {/* Challenge cards */}
      {isLoading ? (
        <div className="flex gap-4 px-4 overflow-x-auto pb-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="shrink-0 w-52"><CardSkeleton /></div>
          ))}
        </div>
      ) : (
        <div className="flex gap-4 px-4 overflow-x-auto pb-2 no-scrollbar">
          {types.map((ct) => (
            <div key={ct.id} className="shrink-0 w-52">
              <ChallengeCard
                challenge={ct}
                isSelected={selected?.id === ct.id}
                onSelect={() => setSelected(ct)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Buy button — only if no active/pending challenge */}
      <AnimatePresence>
        {selected && !activeChallenge && !pendingChallenge && (
          <motion.div
            className="px-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            <motion.button
              className="w-full py-4 rounded-2xl font-bold text-white text-lg relative overflow-hidden"
              style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
              onClick={() => setShowConfirm(true)}
              whileTap={{ scale: 0.97 }}
            >
              <motion.div
                className="absolute inset-0 opacity-20"
                style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }}
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
              Начать испытание — ${selected.price}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Confirm bottom sheet ── */}
      <BottomSheet
        isOpen={showConfirm && !!selected}
        onClose={() => setShowConfirm(false)}
        title="Подтверждение покупки"
      >
        {selected && (
          <div className="p-5 space-y-5">
            {/* Plan summary */}
            <div className="glass-card p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Испытание</span>
                <span className="text-white font-semibold">{selected.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Счёт</span>
                <span className="text-white num font-semibold">${selected.account_size.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Цель P1</span>
                <span className="text-profit num">{selected.profit_target_p1}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Макс. просадка</span>
                <span className="text-loss num">{selected.max_total_loss}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Профит-шер</span>
                <span className="text-profit num">{selected.profit_split_pct}%</span>
              </div>
              <div className="border-t border-bg-border pt-3 flex justify-between">
                <span className="text-text-secondary">Стоимость</span>
                <span className="text-white font-bold text-lg num">${selected.price}</span>
              </div>
            </div>

            {/* Payment wallet */}
            <div
              className="rounded-2xl p-4 space-y-2"
              style={{ background: 'rgba(108,99,255,0.08)', border: '1px solid rgba(108,99,255,0.25)' }}
            >
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <CreditCardIcon size={13} color="#a89fff" />
                Оплата — USDT BEP20
              </p>
              <p className="text-xs text-text-muted">
                Переведите <span className="text-white font-bold num">${selected.price} USDT</span> на кошелёк:
              </p>
              <div
                className="rounded-xl px-3 py-2 flex items-center justify-between gap-2"
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                <span className="text-xs text-white font-mono break-all select-all" style={{ wordBreak: 'break-all' }}>
                  0x075c92cd6e2895c280d540cec4e84617c0378463
                </span>
                <button
                  className="shrink-0 text-xs px-2 py-1 rounded-lg font-semibold"
                  style={{ background: 'rgba(108,99,255,0.3)', color: '#a89fff' }}
                  onClick={() => navigator.clipboard?.writeText('0x075c92cd6e2895c280d540cec4e84617c0378463')}
                >
                  Копировать
                </button>
              </div>
              <p className="text-xs text-text-muted">
                Сеть: <span className="text-profit font-semibold">BEP20 (BSC)</span>
              </p>
            </div>

            {/* How it works */}
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <ClipboardIcon size={13} color="#888" />
                Как это работает
              </p>
              <p className="text-sm text-text-secondary">1. Переведите ${selected.price} USDT на кошелёк выше</p>
              <p className="text-sm text-text-secondary">2. Нажмите кнопку ниже — заявка создана</p>
              <p className="text-sm text-text-secondary">
                3. Отправьте скриншот в бот <span className="text-white font-semibold">@{botUsername}</span>
              </p>
              <p className="text-sm text-text-secondary">4. Администратор активирует испытание после проверки</p>
            </div>

            <motion.button
              className="w-full py-4 rounded-2xl font-bold text-white"
              style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
              onClick={() => purchaseMutation.mutate(selected.id)}
              disabled={purchaseMutation.isPending}
              whileTap={{ scale: 0.97 }}
            >
              {purchaseMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <SpinnerIcon size={18} color="#fff" />
                  Создаём заявку...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <AnimatedCheckIcon size={20} color="#fff" />
                  Я оплатил — создать заявку ${selected.price}
                </span>
              )}
            </motion.button>

            {purchaseError && (
              <p className="text-loss text-sm text-center">{purchaseError}</p>
            )}
          </div>
        )}
      </BottomSheet>

      {/* ── Success sheet (pending_payment created) ── */}
      <BottomSheet
        isOpen={showSuccess}
        onClose={() => setShowSuccess(false)}
        title="Заявка создана!"
      >
        <div className="p-5 space-y-4">
          <div className="text-center">
            <div className="flex justify-center mb-3">
              <ClockIcon size={56} color="#6C63FF" />
            </div>
            <h3 className="text-lg font-bold text-white">Ожидаем подтверждения</h3>
            <p className="text-text-secondary text-sm mt-2">
              Заявка принята. Отправьте скриншот оплаты в бот — администраторы активируют испытание после проверки транзакции.
            </p>
          </div>

          <div
            className="rounded-2xl p-4"
            style={{ background: 'rgba(108,99,255,0.08)', border: '1px solid rgba(108,99,255,0.25)' }}
          >
            <p className="text-xs text-text-secondary mb-2 font-semibold">Следующий шаг:</p>
            <p className="text-sm text-white">
              Откройте бот{' '}
              <span className="font-bold text-profit">@{botUsername}</span>{' '}
              и отправьте скриншот перевода USDT.
            </p>
          </div>

          <motion.button
            className="w-full py-4 rounded-2xl font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
            onClick={() => { setShowSuccess(false); navigate('/dashboard') }}
            whileTap={{ scale: 0.97 }}
          >
            Понятно
          </motion.button>
        </div>
      </BottomSheet>
    </div>
  )
}
