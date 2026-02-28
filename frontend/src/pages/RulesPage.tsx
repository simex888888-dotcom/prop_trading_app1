/**
 * RulesPage — визуальные правила испытания + калькулятор риска.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { challengesApi } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import { RiskMeter } from '@/components/ui/RiskMeter'
import { CardSkeleton } from '@/components/ui/LoadingSkeleton'

type RulesTab = 'rules' | 'calculator'

export function RulesPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const [activeTab, setActiveTab] = useState<RulesTab>('rules')

  const { data: rules, isLoading } = useQuery({
    queryKey: ['challenge-rules', activeChallengeId],
    queryFn: () => challengesApi.getRules(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 30_000,
  })

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <span className="text-5xl">📜</span>
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">Купи испытание, чтобы видеть правила</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <h1 className="text-xl font-bold text-white">Правила</h1>
        {rules && (
          <p className="text-text-secondary text-sm mt-0.5">
            {rules.challenge_type_name} · {rules.phase}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="mx-4 flex gap-1 p-1 bg-bg-border rounded-xl mb-4">
        {(['rules', 'calculator'] as RulesTab[]).map((tab) => (
          <button
            key={tab}
            className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: activeTab === tab ? '#12121A' : 'transparent',
              color: activeTab === tab ? '#fff' : '#4A4A5A',
            }}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'rules' ? '📜 Правила' : '🧮 Калькулятор'}
          </button>
        ))}
      </div>

      {activeTab === 'rules' && (
        isLoading ? <div className="px-4"><CardSkeleton /></div>
          : rules ? <RulesContent rules={rules} />
          : <p className="text-center text-text-muted py-8">Ошибка загрузки правил</p>
      )}

      {activeTab === 'calculator' && (
        <RiskCalculator accountSize={rules?.initial_balance ?? 10000} />
      )}
    </div>
  )
}

function RulesContent({ rules }: { rules: any }) {
  const items = [
    {
      icon: '🎯',
      label: 'Цель по прибыли',
      value: `${rules.profit_target_pct ?? 10}%`,
      progress: Math.min(100, ((rules.current_profit_pct ?? 0) / (rules.profit_target_pct ?? 10)) * 100),
      current: `${(rules.current_profit_pct ?? 0).toFixed(2)}%`,
      color: '#00D4AA',
      passed: (rules.current_profit_pct ?? 0) >= (rules.profit_target_pct ?? 10),
    },
    {
      icon: '🛡️',
      label: 'Дневной лимит убытка',
      value: `-${rules.daily_loss_limit_pct ?? 5}%`,
      progress: Math.min(100, ((rules.daily_loss_used_pct ?? 0) / (rules.daily_loss_limit_pct ?? 5)) * 100),
      current: `-${(rules.daily_loss_used_pct ?? 0).toFixed(2)}%`,
      color: (rules.daily_loss_used_pct ?? 0) >= (rules.daily_loss_limit_pct ?? 5) * 0.8 ? '#FF4757' : '#FFA502',
      passed: false,
    },
    {
      icon: '⚠️',
      label: 'Общий лимит убытка',
      value: `-${rules.total_loss_limit_pct ?? 10}%`,
      progress: Math.min(100, ((rules.total_loss_used_pct ?? 0) / (rules.total_loss_limit_pct ?? 10)) * 100),
      current: `-${(rules.total_loss_used_pct ?? 0).toFixed(2)}%`,
      color: (rules.total_loss_used_pct ?? 0) >= (rules.total_loss_limit_pct ?? 10) * 0.8 ? '#FF4757' : '#FFA502',
      passed: false,
    },
    {
      icon: '📊',
      label: 'Минимум торговых дней',
      value: `${rules.min_trading_days ?? 5} дней`,
      progress: Math.min(100, ((rules.trading_days_count ?? 0) / (rules.min_trading_days ?? 5)) * 100),
      current: `${rules.trading_days_count ?? 0} дней`,
      color: '#6C63FF',
      passed: (rules.trading_days_count ?? 0) >= (rules.min_trading_days ?? 5),
    },
  ]

  return (
    <div className="px-4 space-y-3">
      {/* Progress items */}
      {items.map((item) => (
        <motion.div
          key={item.label}
          className="glass-card p-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span>{item.icon}</span>
              <span className="text-sm font-semibold text-white">{item.label}</span>
            </div>
            <div className="flex items-center gap-2">
              {item.passed && (
                <span className="text-xs text-profit">✓</span>
              )}
              <span className="num text-sm font-bold" style={{ color: item.color }}>
                {item.value}
              </span>
            </div>
          </div>
          {/* Progress bar */}
          <div className="h-2 bg-bg-border rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: item.color }}
              initial={{ width: 0 }}
              animate={{ width: `${item.progress}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="num text-xs text-text-muted">{item.current}</span>
            <span className="num text-xs text-text-muted">{item.value}</span>
          </div>
        </motion.div>
      ))}

      {/* Additional rules */}
      <div className="glass-card p-4">
        <p className="text-sm font-semibold text-white mb-3">Дополнительные ограничения</p>
        <div className="space-y-2">
          <RuleItem
            icon="⏰"
            label="Запрет торговли на новостях"
            value={rules.news_trading_ban ? 'Запрещено' : 'Разрешено'}
            ok={!rules.news_trading_ban}
          />
          <RuleItem
            icon="🌙"
            label="Удержание позиций через ночь"
            value={rules.overnight_positions_allowed ? 'Разрешено' : 'Запрещено'}
            ok={rules.overnight_positions_allowed ?? true}
          />
          <RuleItem
            icon="📅"
            label="Удержание через выходные"
            value={rules.weekend_positions_allowed ? 'Разрешено' : 'Запрещено'}
            ok={rules.weekend_positions_allowed ?? false}
          />
          <RuleItem
            icon="🎯"
            label="Правило консистентности"
            value={rules.consistency_rule ? 'Включено' : 'Выключено'}
            ok={true}
          />
        </div>
      </div>

      {/* Days remaining */}
      {rules.days_remaining !== undefined && (
        <div className="glass-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>⏱️</span>
            <span className="text-sm font-semibold text-white">Дней осталось</span>
          </div>
          <span
            className="num text-lg font-bold"
            style={{ color: rules.days_remaining < 5 ? '#FF4757' : '#FFA502' }}
          >
            {rules.days_remaining}
          </span>
        </div>
      )}
    </div>
  )
}

function RuleItem({ icon, label, value, ok }: {
  icon: string; label: string; value: string; ok: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-sm">{icon}</span>
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      <span
        className="text-xs font-semibold"
        style={{ color: ok ? '#00D4AA' : '#FF4757' }}
      >
        {value}
      </span>
    </div>
  )
}

function RiskCalculator({ accountSize }: { accountSize: number }) {
  const [riskPct, setRiskPct] = useState('1')
  const [entryPrice, setEntryPrice] = useState('')
  const [stopLossPrice, setStopLossPrice] = useState('')
  const [leverage, setLeverage] = useState(10)

  const riskAmount = (accountSize * parseFloat(riskPct || '0')) / 100
  const riskPips = entryPrice && stopLossPrice
    ? Math.abs(parseFloat(entryPrice) - parseFloat(stopLossPrice))
    : 0
  const positionSize = riskPips > 0 && parseFloat(entryPrice) > 0
    ? (riskAmount / riskPips) * parseFloat(entryPrice)
    : 0
  const positionSizeWithLeverage = positionSize
  const contractQty = parseFloat(entryPrice) > 0
    ? positionSizeWithLeverage / parseFloat(entryPrice)
    : 0
  const liquidationPct = leverage > 0 ? (100 / leverage) * 0.9 : 0

  return (
    <div className="px-4 space-y-4">
      {/* Account info */}
      <div className="glass-card p-4 flex items-center justify-between">
        <span className="text-sm text-text-secondary">Размер счёта</span>
        <span className="num font-bold text-white">${accountSize.toLocaleString('en')}</span>
      </div>

      {/* Risk % input */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-white">Риск на сделку</span>
          <span className="num text-lg font-bold" style={{ color: '#FFA502' }}>
            {riskPct}%
          </span>
        </div>
        <input
          type="range"
          min={0.1}
          max={5}
          step={0.1}
          value={riskPct}
          onChange={(e) => setRiskPct(e.target.value)}
          className="w-full accent-brand-primary"
        />
        <div className="flex justify-between text-xs text-text-muted">
          <span>0.1%</span>
          <span className="num text-profit">${riskAmount.toFixed(2)}</span>
          <span>5%</span>
        </div>
        {parseFloat(riskPct) > 2 && (
          <p className="text-xs text-loss text-center">
            ⚠️ Высокий риск — рекомендуется не более 2%
          </p>
        )}
      </div>

      {/* Entry / SL */}
      <div className="glass-card p-4 space-y-3">
        <p className="text-sm font-semibold text-white">Цены</p>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-text-secondary">Цена входа</label>
            <input
              type="number"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              placeholder="0.00"
              className="w-full bg-bg-border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none"
              inputMode="decimal"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-text-secondary">Стоп-лосс</label>
            <input
              type="number"
              value={stopLossPrice}
              onChange={(e) => setStopLossPrice(e.target.value)}
              placeholder="0.00"
              className="w-full bg-bg-border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none"
              inputMode="decimal"
            />
          </div>
        </div>
      </div>

      {/* Leverage */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-white">Плечо</span>
          <span className="num text-lg font-bold text-white">{leverage}x</span>
        </div>
        <input
          type="range"
          min={1}
          max={50}
          value={leverage}
          onChange={(e) => setLeverage(Number(e.target.value))}
          className="w-full accent-brand-primary"
        />
      </div>

      {/* Results */}
      {(contractQty > 0 || riskAmount > 0) && (
        <div className="glass-card p-4 space-y-3">
          <p className="text-sm font-semibold text-white mb-2">Результат расчёта</p>
          <ResultRow label="Риск в USDT" value={`$${riskAmount.toFixed(2)}`} color="#FFA502" />
          {riskPips > 0 && (
            <ResultRow label="Дистанция до SL" value={`$${riskPips.toFixed(4)}`} />
          )}
          {contractQty > 0 && (
            <ResultRow label="Размер позиции" value={`${contractQty.toFixed(4)} контракта`} color="#6C63FF" />
          )}
          <ResultRow
            label="Ликвидация (≈)"
            value={`${liquidationPct.toFixed(1)}% от входа`}
            color="#FF4757"
          />

          {/* Risk meter visual */}
          <div className="flex items-center gap-4 pt-2 border-t border-bg-border">
            <RiskMeter value={parseFloat(riskPct) * 20} size={60} label="Риск" />
            <div className="flex-1 space-y-1">
              <p className="text-xs text-text-secondary">
                {parseFloat(riskPct) <= 1 ? 'Консервативный риск' :
                 parseFloat(riskPct) <= 2 ? 'Умеренный риск' :
                 parseFloat(riskPct) <= 3 ? 'Агрессивный риск' : 'Очень высокий риск'}
              </p>
              <p className="text-xs text-text-muted">
                R/R ratio: {riskPips > 0 && entryPrice ? 'укажи TP для расчёта' : 'нет данных'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ResultRow({ label, value, color = '#fff' }: {
  label: string; value: string; color?: string
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="num text-sm font-bold" style={{ color }}>{value}</span>
    </div>
  )
}
