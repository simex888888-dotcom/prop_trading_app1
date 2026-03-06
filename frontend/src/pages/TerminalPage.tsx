/**
 * TerminalPage — мобильный торговый терминал с ордербуком и слайдером позиции.
 */
import { useState, useEffect, useRef, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { tradingApi, type Position, type Order, type Balance } from '@/api/client'
import { TradingChart } from '@/components/charts/TradingChart'
import { PnLNumber } from '@/components/ui/PnLNumber'
import { useAppStore } from '@/store/appStore'
import { useAuthStore } from '@/store/authStore'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const BYBIT_PUBLIC = 'https://api.bybit.com'

const PAIRS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
  'DOGEUSDT', 'AVAXUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT',
  'NEARUSDT', 'APTUSDT', 'ARBUSDT', 'OPUSDT', 'SUIUSDT',
  'INJUSDT', 'TIAUSDT', 'TONUSDT', 'RUNEUSDT', 'AAVEUSDT',
]

/** Количество знаков после запятой для qty по паре */
function qtyDecimals(symbol: string): number {
  if (symbol.startsWith('BTC')) return 3
  if (symbol.startsWith('ETH')) return 2
  if (['DOGEUSDT', 'XRPUSDT', 'ADAUSDT', 'SHIBUSDT'].includes(symbol)) return 0
  return 1
}

function getErrorMsg(error: unknown): string {
  if (!error) return 'Неизвестная ошибка'
  const e = error as any
  return (
    e?.response?.data?.detail ||
    e?.response?.data?.message ||
    e?.message ||
    'Ошибка ордера'
  )
}

// ─── Orderbook hook ───────────────────────────────────────────────────────────

interface OBLevel { price: number; size: number }
interface Orderbook { asks: OBLevel[]; bids: OBLevel[] }

function useOrderbook(symbol: string, enabled: boolean) {
  return useQuery<Orderbook>({
    queryKey: ['orderbook', symbol],
    queryFn: async () => {
      const resp = await fetch(
        `${BYBIT_PUBLIC}/v5/market/orderbook?category=linear&symbol=${symbol}&limit=8`
      )
      const json = await resp.json()
      const result = json.result
      return {
        asks: (result?.a ?? []).map(([p, s]: [string, string]) => ({
          price: parseFloat(p),
          size: parseFloat(s),
        })),
        bids: (result?.b ?? []).map(([p, s]: [string, string]) => ({
          price: parseFloat(p),
          size: parseFloat(s),
        })),
      }
    },
    enabled,
    refetchInterval: 1_500,
    staleTime: 800,
  })
}

// ─── OrderBook component ──────────────────────────────────────────────────────

function OrderBook({
  symbol,
  onPriceSelect,
  selectedPrice,
}: {
  symbol: string
  onPriceSelect: (price: string) => void
  selectedPrice: string
}) {
  const { data: ob, isLoading } = useOrderbook(symbol, true)

  if (isLoading || !ob) {
    return (
      <div className="rounded-2xl p-3 text-center text-text-muted text-xs" style={{ background: '#0E0E18' }}>
        Загрузка стакана...
      </div>
    )
  }

  const maxSize = Math.max(
    ...ob.asks.map((a) => a.size),
    ...ob.bids.map((b) => b.size),
    1,
  )

  const midPrice =
    ob.asks.length && ob.bids.length
      ? ((ob.asks[ob.asks.length - 1]?.price ?? 0) + (ob.bids[0]?.price ?? 0)) / 2
      : 0

  const spread = ob.asks.length && ob.bids.length
    ? (ob.asks[ob.asks.length - 1].price - ob.bids[0].price).toFixed(2)
    : '—'

  const priceStr = (p: number) =>
    p >= 1000
      ? p.toLocaleString('en', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
      : p.toFixed(4)

  return (
    <div className="rounded-2xl overflow-hidden text-xs" style={{ background: '#0E0E18' }}>
      <div className="px-3 py-2 flex justify-between text-text-muted border-b border-bg-border">
        <span>Цена (USDT)</span>
        <span>Объём</span>
      </div>

      {/* Asks (продажа) — reversed: lowest ask at bottom */}
      {[...ob.asks].reverse().slice(0, 6).map((lvl, i) => {
        const pct = (lvl.size / maxSize) * 100
        const isSelected = selectedPrice === lvl.price.toString()
        return (
          <button
            key={i}
            className="w-full flex justify-between px-3 py-1.5 relative text-left transition-opacity hover:opacity-90"
            style={{
              background: isSelected ? 'rgba(255,71,87,0.15)' : 'transparent',
            }}
            onClick={() => onPriceSelect(lvl.price.toFixed(
              lvl.price >= 1000 ? 1 : 4
            ))}
          >
            {/* Depth bar */}
            <div
              className="absolute right-0 top-0 h-full opacity-20"
              style={{ width: `${pct}%`, background: '#FF4757' }}
            />
            <span className="relative z-10 num font-medium" style={{ color: '#FF6B7A' }}>
              {priceStr(lvl.price)}
            </span>
            <span className="relative z-10 num text-text-muted">{lvl.size.toFixed(2)}</span>
          </button>
        )
      })}

      {/* Spread */}
      <div
        className="px-3 py-1.5 flex justify-between border-y border-bg-border"
        style={{ background: '#12121A' }}
      >
        <span className="num font-bold text-white text-sm">
          {midPrice > 0 ? priceStr(midPrice) : '—'}
        </span>
        <span className="text-text-muted">Спред: {spread}</span>
      </div>

      {/* Bids (покупка) */}
      {ob.bids.slice(0, 6).map((lvl, i) => {
        const pct = (lvl.size / maxSize) * 100
        const isSelected = selectedPrice === lvl.price.toString()
        return (
          <button
            key={i}
            className="w-full flex justify-between px-3 py-1.5 relative text-left transition-opacity hover:opacity-90"
            style={{
              background: isSelected ? 'rgba(0,212,170,0.15)' : 'transparent',
            }}
            onClick={() => onPriceSelect(lvl.price.toFixed(
              lvl.price >= 1000 ? 1 : 4
            ))}
          >
            <div
              className="absolute right-0 top-0 h-full opacity-20"
              style={{ width: `${pct}%`, background: '#00D4AA' }}
            />
            <span className="relative z-10 num font-medium" style={{ color: '#00D4AA' }}>
              {priceStr(lvl.price)}
            </span>
            <span className="relative z-10 num text-text-muted">{lvl.size.toFixed(2)}</span>
          </button>
        )
      })}
    </div>
  )
}

// ─── Main TerminalPage ────────────────────────────────────────────────────────

export function TerminalPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const selectedPair = useAppStore((s) => s.selectedPair)
  const setSelectedPair = useAppStore((s) => s.setSelectedPair)
  const accessToken = useAuthStore((s) => s.accessToken)
  const queryClient = useQueryClient()

  const [timeframe, setTimeframe] = useState('60')
  const [pairSearch, setPairSearch] = useState('')
  const [orderType, setOrderType] = useState<'Market' | 'Limit'>('Market')
  const [side, setSide] = useState<'Buy' | 'Sell'>('Buy')
  const [positionPct, setPositionPct] = useState(10)   // % от баланса
  const [qty, setQty] = useState('')
  const [price, setPrice] = useState('')
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [leverage, setLeverage] = useState(10)
  const [liveEquity, setLiveEquity] = useState<number | null>(null)
  const [livePositions, setLivePositions] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions')
  const [showOB, setShowOB] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)

  // ── WebSocket live updates ─────────────────────────────────────────────────
  useEffect(() => {
    if (!activeChallengeId || !accessToken) return
    const ws = new WebSocket(
      `${WS_URL}/trading/ws/${activeChallengeId}?token=${accessToken}`
    )
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'balance_update') {
          setLiveEquity(msg.data.equity)
          setLivePositions(msg.data.positions ?? [])
        }
      } catch {}
    }
    ws.onerror = () => {}
    return () => ws.close()
  }, [activeChallengeId, accessToken])

  // ── Kline data ─────────────────────────────────────────────────────────────
  // ── Filtered pairs for coin search ────────────────────────────────────────
  const filteredPairs = useMemo(() => {
    const q = pairSearch.trim().toUpperCase()
    if (!q) return PAIRS
    return PAIRS.filter((p) => p.replace('USDT', '').includes(q) || p.includes(q))
  }, [pairSearch])

  const klineInterval = ['1', '3'].includes(timeframe) ? 1_000 : ['5', '15'].includes(timeframe) ? 2_000 : 5_000
  const { data: klines = [] } = useQuery({
    queryKey: ['klines', selectedPair, timeframe],
    queryFn: () => tradingApi.getKline(selectedPair, timeframe),
    refetchInterval: klineInterval,
  })

  // ── Balance ────────────────────────────────────────────────────────────────
  const { data: balance } = useQuery<Balance>({
    queryKey: ['balance', activeChallengeId],
    queryFn: () => tradingApi.getBalance(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 5_000,
  })

  // ── Open orders ────────────────────────────────────────────────────────────
  const { data: orders = [] } = useQuery({
    queryKey: ['orders', activeChallengeId],
    queryFn: () => tradingApi.getOrders(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 5_000,
  })

  const currentPrice = klines.length > 0 ? klines[klines.length - 1].close : 0

  // ── Auto-calc qty from positionPct ─────────────────────────────────────────
  useEffect(() => {
    if (!currentPrice || currentPrice === 0) return
    const avail = balance?.available_balance ?? liveEquity ?? 0
    if (avail <= 0) return
    const positionValue = avail * (positionPct / 100) * leverage
    const raw = positionValue / currentPrice
    const dec = qtyDecimals(selectedPair)
    setQty(raw.toFixed(dec))
  }, [positionPct, balance?.available_balance, liveEquity, currentPrice, leverage, selectedPair])

  // ── Auto-set TP/SL defaults when side or price changes ────────────────────
  useEffect(() => {
    if (!currentPrice) return
    const refP = orderType === 'Limit' && price ? parseFloat(price) : currentPrice
    if (side === 'Buy') {
      setTakeProfit((refP * 1.02).toFixed(refP >= 1000 ? 1 : 4))
      setStopLoss((refP * 0.99).toFixed(refP >= 1000 ? 1 : 4))
    } else {
      setTakeProfit((refP * 0.98).toFixed(refP >= 1000 ? 1 : 4))
      setStopLoss((refP * 1.01).toFixed(refP >= 1000 ? 1 : 4))
    }
  }, [side, selectedPair])

  function applyTPPreset(pct: number) {
    const ref = orderType === 'Limit' && price ? parseFloat(price) : currentPrice
    if (!ref) return
    const val = side === 'Buy'
      ? (ref * (1 + pct / 100))
      : (ref * (1 - pct / 100))
    setTakeProfit(val.toFixed(ref >= 1000 ? 1 : 4))
  }

  function applySLPreset(pct: number) {
    const ref = orderType === 'Limit' && price ? parseFloat(price) : currentPrice
    if (!ref) return
    const val = side === 'Buy'
      ? (ref * (1 - pct / 100))
      : (ref * (1 + pct / 100))
    setStopLoss(val.toFixed(ref >= 1000 ? 1 : 4))
  }

  // ── Place order mutation ───────────────────────────────────────────────────
  const placeMutation = useMutation({
    mutationFn: () => {
      const qtyNum = parseFloat(qty)
      if (!qty || isNaN(qtyNum) || qtyNum <= 0) throw new Error('Укажите количество')
      if (!activeChallengeId) throw new Error('Нет активного испытания')
      return tradingApi.placeOrder({
        symbol: selectedPair,
        side,
        order_type: orderType,
        qty,
        price: orderType === 'Limit' && price ? price : undefined,
        stop_loss: stopLoss || undefined,
        take_profit: takeProfit || undefined,
        challenge_id: activeChallengeId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', activeChallengeId] })
      queryClient.invalidateQueries({ queryKey: ['balance', activeChallengeId] })
    },
  })

  // ── Close all mutation ─────────────────────────────────────────────────────
  const closeAllMutation = useMutation({
    mutationFn: () => tradingApi.closeAllPositions(activeChallengeId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  })

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <span className="text-5xl">⚡</span>
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">Купи испытание, чтобы начать торговать</p>
      </div>
    )
  }

  const availBalance = balance?.available_balance ?? liveEquity ?? 0

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">

      {/* Symbol header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white text-base">{selectedPair.replace('USDT', '/USDT')}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-bg-border text-text-secondary">PERP</span>
        </div>
        <div className="flex items-center gap-3">
          {liveEquity !== null && (
            <div className="text-right">
              <div className="text-xs text-text-secondary">Equity</div>
              <div className="num text-xs font-semibold text-white">
                ${liveEquity.toLocaleString('en', { maximumFractionDigits: 2 })}
              </div>
            </div>
          )}
          <div className="num text-base font-bold text-white">
            ${currentPrice.toLocaleString('en', { maximumFractionDigits: currentPrice < 1 ? 6 : 2 })}
          </div>
        </div>
      </div>

      {/* Coin search + pair selector */}
      <div className="px-4 pt-2 pb-1">
        <input
          type="text"
          value={pairSearch}
          onChange={(e) => setPairSearch(e.target.value)}
          placeholder="Поиск монеты (BTC, ETH...)"
          className="w-full rounded-xl px-3 py-2 text-sm text-white mb-2"
          style={{
            background: '#1A1A2E',
            border: '1px solid rgba(255,255,255,0.08)',
            outline: 'none',
          }}
        />
        <div className="overflow-x-auto">
          <div className="flex gap-1.5" style={{ width: 'max-content' }}>
            {filteredPairs.map((p) => (
              <button
                key={p}
                onClick={() => { setSelectedPair(p); setPairSearch('') }}
                className="px-3 py-1 rounded-lg text-xs font-semibold transition-all shrink-0"
                style={{
                  background: selectedPair === p ? '#6C63FF' : '#1A1A2E',
                  color: selectedPair === p ? '#fff' : '#4A4A6A',
                  border: `1px solid ${selectedPair === p ? '#6C63FF' : '#1E1E2E'}`,
                }}
              >
                {p.replace('USDT', '')}
              </button>
            ))}
            {filteredPairs.length === 0 && (
              <span className="text-text-muted text-xs px-2 py-1">Не найдено</span>
            )}
          </div>
        </div>
      </div>

      {/* Chart */}
      <TradingChart
        data={klines}
        symbol={selectedPair}
        onTimeframeChange={setTimeframe}
        activeTimeframe={timeframe}
        height={260}
      />

      {/* Order form */}
      <div className="px-4 space-y-3 pt-2">

        {/* Buy/Sell + Market/Limit */}
        <div className="flex gap-2">
          <div className="flex rounded-xl overflow-hidden flex-1 border border-bg-border">
            {(['Buy', 'Sell'] as const).map((s) => (
              <button
                key={s}
                className="flex-1 py-2.5 text-sm font-bold transition-all"
                style={{
                  background: side === s
                    ? s === 'Buy' ? 'linear-gradient(135deg,#00D4AA,#00B894)' : 'linear-gradient(135deg,#FF4757,#D63031)'
                    : 'transparent',
                  color: side === s ? '#fff' : '#4A4A5A',
                }}
                onClick={() => setSide(s)}
              >
                {s === 'Buy' ? '🟢 LONG' : '🔴 SHORT'}
              </button>
            ))}
          </div>
          <div className="flex rounded-xl overflow-hidden border border-bg-border">
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

        {/* Стакан (OrderBook) toggle — always shown for Limit, toggle for Market */}
        <div className="flex items-center justify-between">
          <span className="text-text-secondary text-xs font-semibold">📊 Стакан цен</span>
          <button
            className="text-xs px-3 py-1 rounded-lg font-semibold"
            style={{
              background: (showOB || orderType === 'Limit') ? 'rgba(108,99,255,0.2)' : '#1A1A2E',
              color: (showOB || orderType === 'Limit') ? '#6C63FF' : '#4A4A6A',
            }}
            onClick={() => setShowOB((v) => !v)}
          >
            {showOB || orderType === 'Limit' ? 'Скрыть' : 'Показать'}
          </button>
        </div>

        {(showOB || orderType === 'Limit') && (
          <OrderBook
            symbol={selectedPair}
            selectedPrice={price}
            onPriceSelect={(p) => {
              setPrice(p)
              setOrderType('Limit')
            }}
          />
        )}

        {/* Limit price input (shown when Limit mode) */}
        {orderType === 'Limit' && (
          <div>
            <label className="text-text-secondary text-xs mb-1 block">Цена лимит-ордера</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={String(currentPrice.toFixed(2))}
              inputMode="decimal"
              className="w-full bg-bg-border border border-bg-border rounded-xl px-3 py-2.5 text-white text-sm num focus:outline-none"
              style={{ borderColor: price ? 'rgba(108,99,255,0.4)' : '' }}
            />
          </div>
        )}

        {/* Position size slider */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-secondary text-xs font-semibold">Размер позиции</span>
            <span className="num text-sm font-bold text-white">
              {positionPct}%
              {availBalance > 0 && (
                <span className="text-text-muted text-xs ml-1">
                  ≈ ${(availBalance * positionPct / 100).toFixed(2)}
                </span>
              )}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={100}
            step={1}
            value={positionPct}
            onChange={(e) => setPositionPct(Number(e.target.value))}
            className="w-full accent-brand-primary"
          />
          <div className="flex gap-1.5 mt-1.5">
            {[5, 10, 25, 50, 100].map((p) => (
              <button
                key={p}
                className="flex-1 py-1 rounded-lg text-xs font-bold transition-all"
                style={{
                  background: positionPct === p ? '#6C63FF' : '#1A1A2E',
                  color: positionPct === p ? '#fff' : '#4A4A6A',
                }}
                onClick={() => setPositionPct(p)}
              >
                {p}%
              </button>
            ))}
          </div>
          {/* Qty display — always visible */}
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-text-muted text-xs shrink-0">Кол-во:</span>
            <input
              type="number"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              inputMode="decimal"
              className="flex-1 bg-bg-border border border-bg-border rounded-lg px-3 py-1.5 text-white text-xs num focus:outline-none"
              placeholder={currentPrice > 0 ? '0.000' : 'Загрузка...'}
            />
            <span className="text-text-muted text-xs shrink-0">{selectedPair.replace('USDT', '')}</span>
          </div>
        </div>

        {/* Leverage slider */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-text-secondary text-xs font-semibold">Кредитное плечо</span>
            <span className="num text-sm font-bold text-white">{leverage}x</span>
          </div>
          <input
            type="range"
            min={1}
            max={50}
            step={1}
            value={leverage}
            onChange={(e) => setLeverage(Number(e.target.value))}
            className="w-full accent-brand-primary"
          />
          <div className="flex gap-1.5 mt-1">
            {[1, 3, 5, 10, 20, 50].map((l) => (
              <button
                key={l}
                className="flex-1 py-1 rounded-lg text-xs font-bold"
                style={{
                  background: leverage === l ? 'rgba(0,212,170,0.2)' : '#1A1A2E',
                  color: leverage === l ? '#00D4AA' : '#4A4A6A',
                }}
                onClick={() => setLeverage(l)}
              >
                {l}x
              </button>
            ))}
          </div>
        </div>

        {/* TP input with presets */}
        <div>
          <label className="text-text-secondary text-xs mb-1 block">Take Profit</label>
          <input
            type="number"
            value={takeProfit}
            onChange={(e) => setTakeProfit(e.target.value)}
            placeholder="Цена TP"
            inputMode="decimal"
            className="w-full bg-bg-border border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none"
            style={{ borderColor: takeProfit ? 'rgba(0,212,170,0.35)' : '#1E1E2E' }}
          />
          <div className="flex gap-1 mt-1.5">
            {[1, 2, 3, 5, 10].map((p) => (
              <button
                key={p}
                className="flex-1 py-1 rounded-lg text-xs font-semibold"
                style={{ background: '#0E1A14', color: '#00D4AA' }}
                onClick={() => applyTPPreset(p)}
              >
                +{p}%
              </button>
            ))}
          </div>
        </div>

        {/* SL input with presets */}
        <div>
          <label className="text-text-secondary text-xs mb-1 block">Stop Loss</label>
          <input
            type="number"
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            placeholder="Цена SL"
            inputMode="decimal"
            className="w-full bg-bg-border border rounded-xl px-3 py-2 text-white text-sm num focus:outline-none"
            style={{ borderColor: stopLoss ? 'rgba(255,71,87,0.35)' : '#1E1E2E' }}
          />
          <div className="flex gap-1 mt-1.5">
            {[0.5, 1, 2, 3, 5].map((p) => (
              <button
                key={p}
                className="flex-1 py-1 rounded-lg text-xs font-semibold"
                style={{ background: '#1A0E0E', color: '#FF4757' }}
                onClick={() => applySLPreset(p)}
              >
                -{p}%
              </button>
            ))}
          </div>
        </div>

        {/* Place order button */}
        <motion.button
          className="w-full py-4 rounded-2xl font-bold text-white text-base"
          style={{
            background: side === 'Buy'
              ? 'linear-gradient(135deg, #00D4AA, #00B894)'
              : 'linear-gradient(135deg, #FF4757, #D63031)',
            boxShadow: side === 'Buy'
              ? '0 4px 20px rgba(0,212,170,0.3)'
              : '0 4px 20px rgba(255,71,87,0.3)',
            opacity: placeMutation.isPending ? 0.7 : 1,
          }}
          onClick={() => placeMutation.mutate()}
          disabled={placeMutation.isPending || !qty || parseFloat(qty) <= 0}
          whileTap={{ scale: 0.97 }}
        >
          {placeMutation.isPending
            ? '⏳ Отправка...'
            : `${side === 'Buy' ? '🟢 LONG' : '🔴 SHORT'} ${qty || '0'} ${selectedPair.replace('USDT', '')} · ${leverage}x`}
        </motion.button>

        {/* Error */}
        <AnimatePresence>
          {placeMutation.isError && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-xl px-4 py-3 text-xs"
              style={{ background: 'rgba(255,71,87,0.1)', color: '#FF4757', border: '1px solid rgba(255,71,87,0.2)' }}
            >
              ⚠️ {getErrorMsg(placeMutation.error)}
            </motion.div>
          )}
          {placeMutation.isSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-xl px-4 py-3 text-xs text-center"
              style={{ background: 'rgba(0,212,170,0.1)', color: '#00D4AA', border: '1px solid rgba(0,212,170,0.2)' }}
            >
              ✅ Ордер размещён!
            </motion.div>
          )}
        </AnimatePresence>
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
              livePositions.map((pos, i) => <PositionRow key={i} pos={pos} />)
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

// ─── Sub-components ───────────────────────────────────────────────────────────

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
      <PnLNumber value={pos.pnl ?? 0} size="sm" />
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
        <span className="text-xs text-text-muted">{order.order_type}</span>
      </div>
      <div className="text-right">
        <div className="num text-xs text-white">{order.price ? `$${order.price.toFixed(2)}` : 'Market'}</div>
        <div className="num text-xs text-text-muted">{order.qty}</div>
      </div>
    </div>
  )
}
