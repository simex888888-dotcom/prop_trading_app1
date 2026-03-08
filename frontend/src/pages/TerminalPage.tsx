/**
 * TerminalPage — полноценный мобильный торговый терминал.
 * Фичи: TP/SL редактирование, частичное закрытие, реал-тайм через WS.
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

interface LiveData {
  equity: number
  wallet_balance: number
  unrealized_pnl: number
  positions: any[]
}

export function TerminalPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const selectedPair = useAppStore((s) => s.selectedPair)
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
  const [liveData, setLiveData] = useState<LiveData | null>(null)
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions')
  const wsRef = useRef<WebSocket | null>(null)

  // WebSocket реал-тайм + автореконнект
  useEffect(() => {
    if (!activeChallengeId || !accessToken) return

    let closed = false
    const connect = () => {
      if (closed) return
      const ws = new WebSocket(
        `${WS_URL}/trading/ws/${activeChallengeId}?token=${accessToken}`
      )
      wsRef.current = ws
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'balance_update') {
            setLiveData(msg.data)
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          }
        } catch {}
      }
      ws.onclose = () => { if (!closed) setTimeout(connect, 3000) }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => { closed = true; wsRef.current?.close() }
  }, [activeChallengeId, accessToken])

  const { data: klines = [] } = useQuery({
    queryKey: ['klines', selectedPair, timeframe],
    queryFn: () => tradingApi.getKline(selectedPair, timeframe),
    refetchInterval: 10_000,
  })

  const { data: orders = [] } = useQuery({
    queryKey: ['orders', activeChallengeId],
    queryFn: () => tradingApi.getOrders(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 5_000,
  })

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
      setQty(''); setPrice(''); setStopLoss(''); setTakeProfit('')
    },
  })

  const closeAllMutation = useMutation({
    mutationFn: () => tradingApi.closeAllPositions(activeChallengeId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  })

  const currentPrice = klines.length > 0 ? klines[klines.length - 1].close : 0
  const positions = liveData?.positions ?? []
  const equity = liveData?.equity ?? null
  const unrealizedPnl = liveData?.unrealized_pnl ?? 0

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
      {/* Шапка */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white text-sm">{selectedPair}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-bg-border text-text-secondary">PERP</span>
        </div>
        <div className="flex items-center gap-4">
          {equity !== null && (
            <div className="text-right">
              <div className="text-[10px] text-text-muted uppercase tracking-wide">Equity</div>
              <div className={`num text-base font-bold ${unrealizedPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                ${equity.toLocaleString('en', { maximumFractionDigits: 2 })}
              </div>
              {unrealizedPnl !== 0 && (
                <div className={`num text-[10px] ${unrealizedPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {unrealizedPnl >= 0 ? '+' : ''}{unrealizedPnl.toFixed(2)}
                </div>
              )}
            </div>
          )}
          <div className="num text-lg font-bold text-white">
            ${currentPrice.toLocaleString('en', { maximumFractionDigits: 4 })}
          </div>
        </div>
      </div>

      <TradingChart data={klines} symbol={selectedPair} onTimeframeChange={setTimeframe} activeTimeframe={timeframe} height={280} />

      {/* Форма */}
      <div className="px-4 space-y-3 pt-3">
        <div className="flex gap-2">
          <div className="flex rounded-xl overflow-hidden flex-1" style={{ border: '1px solid #1E1E2E' }}>
            {(['Buy', 'Sell'] as const).map((s) => (
              <button key={s} className="flex-1 py-2.5 text-sm font-bold transition-all"
                style={{ background: side === s ? (s === 'Buy' ? '#00D4AA' : '#FF4757') : 'transparent', color: side === s ? '#fff' : '#4A4A5A' }}
                onClick={() => setSide(s)}>
                {s === 'Buy' ? '▲ LONG' : '▼ SHORT'}
              </button>
            ))}
          </div>
          <div className="flex rounded-xl overflow-hidden" style={{ border: '1px solid #1E1E2E' }}>
            {(['Market', 'Limit'] as const).map((t) => (
              <button key={t} className="px-3 py-2 text-xs font-semibold transition-all"
                style={{ background: orderType === t ? '#1E1E2E' : 'transparent', color: orderType === t ? '#fff' : '#4A4A5A' }}
                onClick={() => setOrderType(t)}>{t}</button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <OrderInput label="Количество" value={qty} onChange={setQty} placeholder="0.001" />
          {orderType === 'Limit' && <OrderInput label="Цена" value={price} onChange={setPrice} placeholder={String(currentPrice)} />}
          <OrderInput label="Стоп-лосс" value={stopLoss} onChange={setStopLoss} placeholder="Цена SL" />
          <OrderInput label="Тейк-профит" value={takeProfit} onChange={setTakeProfit} placeholder="Цена TP" />
        </div>

        <div className="flex items-center gap-3">
          <span className="text-text-secondary text-xs shrink-0">Плечо</span>
          <input type="range" min={1} max={50} value={leverage}
            onChange={(e) => setLeverage(Number(e.target.value))} className="flex-1 accent-brand-primary" />
          <span className="num text-sm font-bold text-white w-10 text-right">{leverage}x</span>
        </div>

        <motion.button className="w-full py-4 rounded-2xl font-bold text-white text-base"
          style={{
            background: side === 'Buy' ? 'linear-gradient(135deg, #00D4AA, #00B894)' : 'linear-gradient(135deg, #FF4757, #D63031)',
            boxShadow: side === 'Buy' ? '0 4px 20px rgba(0,212,170,0.3)' : '0 4px 20px rgba(255,71,87,0.3)',
          }}
          onClick={() => placeMutation.mutate()} disabled={placeMutation.isPending || !qty} whileTap={{ scale: 0.97 }}>
          {placeMutation.isPending ? '⏳ Отправка...' : `${side === 'Buy' ? '▲ LONG' : '▼ SHORT'} ${qty || '0'} ${selectedPair}`}
        </motion.button>

        {placeMutation.isError && (
          <p className="text-loss text-xs text-center">
            {(placeMutation.error as any)?.response?.data?.detail ?? 'Ошибка при открытии позиции'}
          </p>
        )}
      </div>

      {/* Позиции/Ордера */}
      <div className="px-4 mt-4">
        <div className="flex gap-1 p-1 bg-bg-border rounded-xl mb-3">
          {(['positions', 'orders'] as const).map((tab) => (
            <button key={tab} className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
              style={{ background: activeTab === tab ? '#12121A' : 'transparent', color: activeTab === tab ? '#fff' : '#4A4A5A' }}
              onClick={() => setActiveTab(tab)}>
              {tab === 'positions' ? `Позиции (${positions.length})` : `Ордера (${orders.length})`}
            </button>
          ))}
        </div>

        {activeTab === 'positions' && (
          <div className="space-y-2">
            {positions.length === 0
              ? <p className="text-text-muted text-sm text-center py-4">Нет открытых позиций</p>
              : positions.map((pos: any, i: number) => (
                  <PositionRow key={`${pos.symbol}-${i}`} pos={pos} challengeId={activeChallengeId!}
                    onChanged={() => queryClient.invalidateQueries({ queryKey: ['positions'] })} />
                ))}
            {positions.length > 0 && (
              <motion.button className="w-full py-3 rounded-xl text-sm font-semibold text-loss"
                style={{ background: 'rgba(255,71,87,0.1)', border: '1px solid rgba(255,71,87,0.2)' }}
                onClick={() => closeAllMutation.mutate()} disabled={closeAllMutation.isPending} whileTap={{ scale: 0.97 }}>
                ✕ Закрыть все позиции
              </motion.button>
            )}
          </div>
        )}

        {activeTab === 'orders' && (
          <div className="space-y-2">
            {orders.length === 0
              ? <p className="text-text-muted text-sm text-center py-4">Нет активных ордеров</p>
              : orders.map((order) => (
                  <OrderRow key={order.order_id} order={order} challengeId={activeChallengeId!}
                    onCancelled={() => queryClient.invalidateQueries({ queryKey: ['orders'] })} />
                ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── PositionRow: TP/SL + частичное закрытие ───────────────────────────────────

function PositionRow({ pos, challengeId, onChanged }: { pos: any; challengeId: number; onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [tpInput, setTpInput] = useState(String(pos.take_profit ?? ''))
  const [slInput, setSlInput] = useState(String(pos.stop_loss ?? ''))
  const [closeQty, setCloseQty] = useState(50)
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  const isLong = pos.side === 'Buy'
  const pnl = pos.pnl ?? pos.unrealized_pnl ?? 0
  const size = Number(pos.size)

  const notify = (text: string) => { setMsg(text); setTimeout(() => setMsg(''), 3000) }

  const saveTPSL = async () => {
    setSaving(true)
    try {
      await tradingApi.modifyTradingStop({ challenge_id: challengeId, symbol: pos.symbol, take_profit: tpInput || '0', stop_loss: slInput || '0' })
      notify('✅ TP/SL обновлён')
      onChanged()
    } catch (e: any) { notify('❌ ' + (e?.response?.data?.detail ?? 'Ошибка')) }
    setSaving(false)
  }

  const partialClose = async () => {
    const qtyToClose = ((closeQty / 100) * size).toFixed(3)
    setSaving(true)
    try {
      await tradingApi.partialClose({ challenge_id: challengeId, symbol: pos.symbol, side: pos.side, qty: qtyToClose })
      notify(`✅ Закрыто ${closeQty}%`)
      onChanged()
    } catch (e: any) { notify('❌ ' + (e?.response?.data?.detail ?? 'Ошибка')) }
    setSaving(false)
  }

  return (
    <div className="glass-card overflow-hidden">
      <button className="w-full p-3 flex items-center justify-between" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded font-bold ${isLong ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'}`}>
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          <span className="text-sm font-semibold text-white">{pos.symbol}</span>
          <span className="text-xs text-text-muted num">{size}</span>
        </div>
        <div className="flex items-center gap-2">
          <PnLNumber value={pnl} size="sm" />
          <span className="text-text-muted text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
            className="px-3 pb-3 space-y-3 border-t border-bg-border">

            <div className="flex gap-4 pt-2 text-xs text-text-muted">
              <span>Avg: <span className="num text-white">{pos.avg_price?.toFixed(2) ?? '—'}</span></span>
              <span>TP: <span className="num text-profit">{pos.take_profit ?? '—'}</span></span>
              <span>SL: <span className="num text-loss">{pos.stop_loss ?? '—'}</span></span>
            </div>

            {/* TP / SL */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-text-secondary">Изменить TP / SL</p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-profit block mb-1">Take Profit</label>
                  <input type="number" value={tpInput} onChange={(e) => setTpInput(e.target.value)}
                    placeholder="0 = снять"
                    className="w-full bg-bg-border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none border border-transparent focus:border-profit"
                    inputMode="decimal" />
                </div>
                <div>
                  <label className="text-[10px] text-loss block mb-1">Stop Loss</label>
                  <input type="number" value={slInput} onChange={(e) => setSlInput(e.target.value)}
                    placeholder="0 = снять"
                    className="w-full bg-bg-border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none border border-transparent focus:border-loss"
                    inputMode="decimal" />
                </div>
              </div>
              <button className="w-full py-2 rounded-xl text-xs font-bold text-white"
                style={{ background: '#6C63FF' }} onClick={saveTPSL} disabled={saving}>
                {saving ? '...' : '💾 Сохранить TP/SL'}
              </button>
            </div>

            {/* Частичное закрытие */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-text-secondary">Частичное закрытие</p>
              <div className="flex items-center gap-3">
                <input type="range" min={5} max={100} step={5} value={closeQty}
                  onChange={(e) => setCloseQty(Number(e.target.value))} className="flex-1 accent-loss" />
                <span className="num text-sm font-bold text-white w-12 text-right">{closeQty}%</span>
              </div>
              <p className="text-xs text-text-muted text-center">
                Закрыть {((closeQty / 100) * size).toFixed(3)} из {size}
              </p>
              <div className="flex gap-1">
                {[25, 50, 75, 100].map((pct) => (
                  <button key={pct} className="flex-1 py-1.5 rounded-lg text-xs font-semibold"
                    style={{ background: closeQty === pct ? 'rgba(255,71,87,0.3)' : 'rgba(255,71,87,0.1)', color: '#FF4757' }}
                    onClick={() => setCloseQty(pct)}>{pct}%</button>
                ))}
              </div>
              <button className="w-full py-2 rounded-xl text-xs font-bold"
                style={{ background: 'rgba(255,71,87,0.15)', color: '#FF4757' }}
                onClick={partialClose} disabled={saving}>
                {saving ? '...' : `✕ Закрыть ${closeQty}%`}
              </button>
            </div>

            {msg && (
              <p className="text-xs text-center font-semibold"
                style={{ color: msg.startsWith('✅') ? '#00D4AA' : '#FF4757' }}>{msg}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── OrderRow ──────────────────────────────────────────────────────────────────

function OrderRow({ order, challengeId, onCancelled }: { order: Order; challengeId: number; onCancelled: () => void }) {
  const [cancelling, setCancelling] = useState(false)
  const cancel = async () => {
    setCancelling(true)
    try { await tradingApi.cancelOrder(order.order_id, challengeId, order.symbol); onCancelled() } catch {}
    setCancelling(false)
  }
  return (
    <div className="glass-card p-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={`text-xs px-2 py-0.5 rounded font-bold ${order.side === 'Buy' ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'}`}>
          {order.side}
        </span>
        <div>
          <span className="text-sm font-semibold text-white">{order.symbol}</span>
          <div className="text-xs text-text-muted">{order.order_type}</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className="num text-xs text-white">{order.price ? `$${order.price.toFixed(2)}` : 'Market'}</div>
          <div className="num text-xs text-text-muted">{order.qty}</div>
        </div>
        <button className="px-2 py-1.5 rounded-lg text-xs font-semibold"
          style={{ background: 'rgba(255,71,87,0.15)', color: '#FF4757' }}
          onClick={cancel} disabled={cancelling}>{cancelling ? '...' : '✕'}</button>
      </div>
    </div>
  )
}

// ── Поле ввода ────────────────────────────────────────────────────────────────

function OrderInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="space-y-1">
      <label className="text-text-secondary text-xs">{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-bg-border border border-bg-border rounded-xl px-3 py-2.5 text-white text-sm num focus:outline-none focus:border-brand-primary/50"
        inputMode="decimal" />
    </div>
  )
}
