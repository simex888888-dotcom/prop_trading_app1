/**
 * ChallengesPage — выбор и покупка испытания (RPG-карточки).
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

export function ChallengesPage() {
  const [selected, setSelected] = useState<ChallengeType | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
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
    onSuccess: (challenge) => {
      queryClient.invalidateQueries({ queryKey: ['my-challenges'] })
      setActiveChallenge(challenge)
      setShowConfirm(false)
      navigate('/dashboard')
    },
  })

  const activeChallenge = myChallenges.find(
    (c) => c.status === 'phase1' || c.status === 'phase2' || c.status === 'funded'
  )

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

      {/* Challenge cards horizontal scroll */}
      {isLoading ? (
        <div className="flex gap-4 px-4 overflow-x-auto pb-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="shrink-0 w-52">
              <CardSkeleton />
            </div>
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

      {/* Buy button */}
      <AnimatePresence>
        {selected && (
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

      {/* Confirm bottom sheet */}
      <BottomSheet
        isOpen={showConfirm && !!selected}
        onClose={() => setShowConfirm(false)}
        title="Подтверждение покупки"
      >
        {selected && (
          <div className="p-5 space-y-5">
            <div className="glass-card p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Испытание</span>
                <span className="text-white font-semibold">{selected.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Счёт</span>
                <span className="text-white num font-semibold">
                  ${selected.account_size.toLocaleString()}
                </span>
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

            <p className="text-text-muted text-xs text-center">
              Demo-счёт на Bybit будет создан автоматически
            </p>

            <motion.button
              className="w-full py-4 rounded-2xl font-bold text-white"
              style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
              onClick={() => purchaseMutation.mutate(selected.id)}
              disabled={purchaseMutation.isPending}
              whileTap={{ scale: 0.97 }}
            >
              {purchaseMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.div
                    className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                  />
                  Создаём счёт...
                </span>
              ) : (
                `Оплатить $${selected.price} и начать`
              )}
            </motion.button>

            {purchaseMutation.isError && (
              <p className="text-loss text-sm text-center">
                Ошибка при создании испытания. Попробуйте позже.
              </p>
            )}
          </div>
        )}
      </BottomSheet>
    </div>
  )
}
