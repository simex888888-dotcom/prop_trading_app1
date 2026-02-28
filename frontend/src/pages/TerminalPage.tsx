/**
 * TerminalPage — полноценный мобильный торговый терминал.
 */
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { tradingApi, type Position, type Order } from '@/api/client'
import { TradingChart } from '@/components/charts/TradingChart'
import { PnLNumber } from '@/components/ui/PnLNumber'
import { useAppStore } from '@/store/appStore'
import { useAuthStore } from '@/store/authStore'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export function TerminalPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const selectedPair = useAppStore((s) => s.selectedPair)
  const setSelectedPair = useAppStore((s) => s.setSelectedPair)
  const accessToken = useAuthStore((s) => s.accessToken)
  const queryClient = useQueryClient()

  const [timeframe, setTimeframe] = useState('60')
  const [orderType, setOrderType] = useState<'Market' | 'Limit'>('Market')
  const [side, setSide] = useState<'Buy' | 'Sell'>('Buy')
  const [qty, setQty] = useState('')
  const [price, setPrice] = useState('')
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [leverage, setLeverage] = useState(10)
  const [liveEquity, setLiveEquity] = useState<number | null>(null)
  const [livePositions, setLivePositions] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions')

  const wsRef = useRef<WebSocket | null>(null)

  // WebSocket for real-time updates
  useEffect(() => {
    if (!activeChallengeId || !accessToken) return
    const ws = new WebSocket(
      `${WS_URL}/trading/ws/${activeChallengeId}?token=${accessToken}`
    )
    wsRef.current = ws
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'balance_update') {
        setLiveEquity(msg.data.equity)
        setLivePositions(msg.data.positions ?? [])
      }
    }
    ws.onerror = () => {}
    return () => ws.close()
  }, [activeChallengeId, accessToken])

  // Kline data
  const { data: klines = [] } = useQuery({
    queryKey: ['klines', selectedPair, timeframe],
    queryFn: () => tradingApi.getKline(selectedPair, timeframe),
    refetchInterval: 10_000,
  })

  // Open orders
  const { data: orders = [] } = useQuery({
    queryKey: ['orders', activeChallengeId],
    queryFn: () => tradingApi.getOrders(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 5_000,
  })

  // Place order mutation
  const placeMutation = useMutation({
    mutationFn: () => tradingApi.placeOrder({
      symbol: selectedPair,
      side,
      order_type: orderType,
      qty,
      price: orderType === 'Limit' ? price : undefined,
      stop_loss: stopLoss || undefined,
      take_profit: takeProfit || undefined,
      challenge_id: activeChallengeId!,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', activeChallengeId] })
      setQty('')
      setPrice('')
      setStopLoss('')
      setTakeProfit('')
    },
  })

  // Close all mutation
  const closeAllMutation = useMutation({
    mutationFn: () => tradingApi.closeAllPositions(activeChallengeId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  })

  const currentPrice = klines.length > 0 ? klines[klines.length - 1].close : 0

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <span className="text-5xl">⚡</span>
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">Купи испытание, чтобы начать торговать</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Symbol header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white">{selectedPair}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-bg-border text-text-secondary">PERP</span>
        </div>
        <div className="flex items-center gap-3">
          {liveEquity !== null && (
            <div className="text-right">
              <div className="text-xs text-text-secondary">Equity</div>
              <div className="num text-sm font-semibold text-white">
                ${liveEquity.toLocaleString('en', { maximumFractionDigits: 2 })}
              </div>
            </div>
          )}
          <div className="num text-lg font-bold text-white">
            ${currentPrice.toLocaleString('en', { maximumFractionDigits: 4 })}
          </div>
        </div>
      </div>

      {/* Chart */}
      <TradingChart
        data={klines}
        symbol={selectedPair}
        onTimeframeChange={setTimeframe}
        activeTimeframe={timeframe}
        height={300}
      />

      {/* Order form */}
      <div className="px-4 space-y-3 pt-3">
        {/* Buy/Sell + Order type */}
        <div className="flex gap-2">
          <div className="flex rounded-xl overflow-hidden flex-1" style={{ border: '1px solid #1E1E2E' }}>
            {(['Buy', 'Sell'] as const).map((s) => (
              <button
                key={s}
                className="flex-1 py-2.5 text-sm font-bold transition-all"
                style={{
                  background: side === s
                    ? s === 'Buy' ? '#00D4AA' : '#FF4757'
                    : 'transparent',
                  color: side === s ? '#fff' : '#4A4A5A',
                }}
                onClick={() => setSide(s)}
              >
                {s === 'Buy' ? '🟢 LONG' : '🔴 SHORT'}
              </button>
            ))}
          </div>
          <div className="flex rounded-xl overflow-hidden" style={{ border: '1px solid #1E1E2E' }}>
            {(['Market', 'Limit'] as const).map((t) => (
              <button
                key={t}
                className="px-3 py-2 text-xs font-semibold transition-all"
                style={{
                  background: orderType === t ? '#1E1E2E' : 'transparent',
                  color: orderType === t ? '#fff' : '#4A4A5A',
                }}
                onClick={() => setOrderType(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-2 gap-2">
          <OrderInput label="Количество" value={qty} onChange={setQty} placeholder="0.001" />
          {orderType === 'Limit' && (
            <OrderInput label="Цена" value={price} onChange={setPrice} placeholder={String(currentPrice)} />
          )}
          <OrderInput label="Стоп-лосс" value={stopLoss} onChange={setStopLoss} placeholder="Цена SL" />
          <OrderInput label="Тейк-профит" value={takeProfit} onChange={setTakeProfit} placeholder="Цена TP" />
        </div>

        {/* Quick SL buttons */}
        <div className="flex gap-2">
          {['1R', '2R', '3R'].map((r) => (
            <button
              key={r}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold text-text-secondary"
              style={{ background: '#1E1E2E' }}
            >
              {r}
            </button>
          ))}
          <button
            className="flex-1 py-1.5 rounded-lg text-xs font-semibold"
            style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
          >
            Авто-риск
          </button>
        </div>

        {/* Leverage */}
        <div className="flex items-center gap-3">
          <span className="text-text-secondary text-xs shrink-0">Плечо</span>
          <input
            type="range"
            min={1}
            max={50}
            value={leverage}
            onChange={(e) => setLeverage(Number(e.target.value))}
            className="flex-1 accent-brand-primary"
          />
          <span className="num text-sm font-bold text-white w-10 text-right">{leverage}x</span>
        </div>

        {/* Place order button */}
        <motion.button
          className="w-full py-4 rounded-2xl font-bold text-white text-base"
          style={{
            background: side === 'Buy'
              ? 'linear-gradient(135deg, #00D4AA, #00B894)'
              : 'linear-gradient(135deg, #FF4757, #D63031)',
            boxShadow: side === 'Buy' ? '0 4px 20px rgba(0,212,170,0.3)' : '0 4px 20px rgba(255,71,87,0.3)',
          }}
          onClick={() => placeMutation.mutate()}
          disabled={placeMutation.isPending || !qty}
          whileTap={{ scale: 0.97 }}
        >
          {placeMutation.isPending ? '⏳ Отправка...' : `${side === 'Buy' ? '🟢 LONG' : '🔴 SHORT'} ${qty || '0'} ${selectedPair}`}
        </motion.button>

        {placeMutation.isError && (
          <p className="text-loss text-xs text-center">
            Ошибка ордера. Проверьте параметры.
          </p>
        )}
      </div>

      {/* Positions / Orders tabs */}
      <div className="px-4 mt-4">
        <div className="flex gap-1 p-1 bg-bg-border rounded-xl mb-3">
          {(['positions', 'orders'] as const).map((tab) => (
            <button
              key={tab}
              className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: activeTab === tab ? '#12121A' : 'transparent',
                color: activeTab === tab ? '#fff' : '#4A4A5A',
              }}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'positions' ? `Позиции (${livePositions.length})` : `Ордера (${orders.length})`}
            </button>
          ))}
        </div>

        {activeTab === 'positions' && (
          <div className="space-y-2">
            {livePositions.length === 0 ? (
              <p className="text-text-muted text-sm text-center py-4">Нет открытых позиций</p>
            ) : (
              livePositions.map((pos, i) => (
                <PositionRow key={i} pos={pos} />
              ))
            )}
            {livePositions.length > 0 && (
              <motion.button
                className="w-full py-3 rounded-xl text-sm font-semibold text-loss"
                style={{ background: 'rgba(255,71,87,0.1)', border: '1px solid rgba(255,71,87,0.2)' }}
                onClick={() => closeAllMutation.mutate()}
                disabled={closeAllMutation.isPending}
                whileTap={{ scale: 0.97 }}
              >
                ✕ Закрыть все позиции
              </motion.button>
            )}
          </div>
        )}

        {activeTab === 'orders' && (
          <div className="space-y-2">
            {orders.length === 0 ? (
              <p className="text-text-muted text-sm text-center py-4">Нет активных ордеров</p>
            ) : (
              orders.map((order) => <OrderRow key={order.order_id} order={order} />)
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function OrderInput({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <div className="space-y-1">
      <label className="text-text-secondary text-xs">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-bg-border border border-bg-border rounded-xl px-3 py-2.5 text-white text-sm num focus:outline-none focus:border-brand-primary/50"
        inputMode="decimal"
      />
    </div>
  )
}

function PositionRow({ pos }: { pos: any }) {
  const isLong = pos.side === 'Buy'
  return (
    <div className="glass-card p-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={`text-xs px-2 py-0.5 rounded font-bold ${isLong ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'}`}>
          {isLong ? 'LONG' : 'SHORT'}
        </span>
        <span className="text-sm font-semibold text-white">{pos.symbol}</span>
        <span className="text-xs text-text-muted num">{pos.size}</span>
      </div>
      <PnLNumber value={pos.pnl} size="sm" />
    </div>
  )
}

function OrderRow({ order }: { order: Order }) {
  return (
    <div className="glass-card p-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={`text-xs px-2 py-0.5 rounded font-bold ${order.side === 'Buy' ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'}`}>
          {order.side}
        </span>
        <span className="text-sm font-semibold text-white">{order.symbol}</span>
      </div>
      <div className="text-right">
        <div className="num text-xs text-white">${order.price?.toFixed(2) ?? 'Market'}</div>
        <div className="num text-xs text-text-muted">{order.qty}</div>
      </div>
    </div>
  )
}
