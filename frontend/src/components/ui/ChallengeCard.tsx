/**
 * ChallengeCard — карточка испытания в RPG-стиле.
 */
import { motion } from 'framer-motion'
import type { ChallengeType } from '@/api/client'

interface ChallengeCardProps {
  challenge: ChallengeType
  isSelected?: boolean
  onSelect: () => void
}

const RANK_ICONS: Record<string, string> = {
  'Isotope $5K': '⚛️',
  'Reagent $10K': '🧪',
  'Catalyst $25K': '⚗️',
  'Molecule $50K': '🔬',
  'Crystal $100K': '💎',
  'Nucleus $200K': '☢️',
}

export function ChallengeCard({ challenge, isSelected, onSelect }: ChallengeCardProps) {
  const icon = RANK_ICONS[challenge.name] ?? '🎯'
  const sizeLabel = challenge.account_size >= 1000
    ? `$${(challenge.account_size / 1000).toFixed(0)}K`
    : `$${challenge.account_size}`

  return (
    <motion.div
      className="relative rounded-2xl overflow-hidden cursor-pointer select-none"
      style={{
        background: challenge.gradient_bg ?? 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        border: isSelected ? '2px solid #6C63FF' : '2px solid rgba(255,255,255,0.06)',
        boxShadow: isSelected ? '0 0 24px rgba(108, 99, 255, 0.4)' : 'none',
        minWidth: 200,
        minHeight: 260,
      }}
      whileTap={{ scale: 0.97 }}
      animate={isSelected ? { y: -4 } : { y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      onClick={onSelect}
    >
      {/* Background shimmer */}
      <div className="absolute inset-0 opacity-10"
        style={{ background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 8px)' }}
      />

      <div className="relative p-5 flex flex-col h-full gap-3">
        {/* Icon + Size */}
        <div className="flex items-start justify-between">
          <span className="text-4xl">{icon}</span>
          <div className="text-right">
            {challenge.is_instant && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-warning/20 text-warning border border-warning/30">
                ⚡ Instant
              </span>
            )}
            {challenge.is_refundable && (
              <div className="text-xs text-profit mt-1">↩ Refundable</div>
            )}
          </div>
        </div>

        {/* Name */}
        <div>
          <h3 className="font-bold text-xl text-white">{sizeLabel}</h3>
          <p className="text-text-secondary text-xs mt-0.5">{challenge.name}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 text-xs mt-auto">
          <StatItem label="Цель P1" value={`${challenge.profit_target_p1}%`} color="text-profit" />
          <StatItem label="Цель P2" value={`${challenge.profit_target_p2}%`} color="text-profit" />
          <StatItem label="Дн. просадка" value={`${challenge.max_daily_loss}%`} color="text-loss" />
          <StatItem label="Общ. просадка" value={`${challenge.max_total_loss}%`} color="text-loss" />
          <StatItem label="Мин. дней" value={String(challenge.min_trading_days)} />
          <StatItem label="Плечо" value={`${challenge.max_leverage}x`} />
        </div>

        {/* Profit split */}
        <div className="flex items-center justify-between pt-2 border-t border-white/10">
          <span className="text-text-secondary text-xs">Профит-шер</span>
          <span className="text-profit font-bold text-sm num">{challenge.profit_split_pct}%</span>
        </div>

        {/* Price */}
        <div className="flex items-center justify-between">
          <span className="text-text-secondary text-xs">Стоимость</span>
          <span className="text-white font-bold text-lg num">${challenge.price}</span>
        </div>

        {/* Select button */}
        <motion.button
          className="w-full py-2.5 rounded-xl font-semibold text-sm transition-all"
          style={{
            background: isSelected
              ? 'linear-gradient(135deg, #6C63FF, #00D4AA)'
              : 'rgba(108, 99, 255, 0.15)',
            border: '1px solid rgba(108, 99, 255, 0.3)',
            color: isSelected ? '#fff' : '#6C63FF',
          }}
          whileTap={{ scale: 0.97 }}
        >
          {isSelected ? '✓ Выбрано' : 'Выбрать путь'}
        </motion.button>
      </div>
    </motion.div>
  )
}

function StatItem({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-black/20 rounded-lg px-2 py-1.5">
      <div className="text-text-muted text-[10px]">{label}</div>
      <div className={`font-semibold num ${color}`}>{value}</div>
    </div>
  )
}
