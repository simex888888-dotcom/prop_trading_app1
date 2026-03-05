/**
 * HistoryPage — история сделок с фильтрами, пагинацией и графиком equity.
 */
import { useState, useCallback } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { statsApi, tradingApi, type TradeHistory } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import { EquitySparkline } from '@/components/charts/EquitySparkline'
import { PnLNumber } from '@/components/ui/PnLNumber'
import { DashboardSkeleton } from '@/components/ui/LoadingSkeleton'

type FilterSide = 'All' | 'Buy' | 'Sell'
type FilterResult = 'All' | 'Win' | 'Loss'

export function HistoryPage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const [filterSide, setFilterSide] = useState<FilterSide>('All')
  const [filterResult, setFilterResult] = useState<FilterResult>('All')
  const [shareVisible, setShareVisible] = useState<TradeHistory | null>(null)

  const { data: equityData = [] } = useQuery({
    queryKey: ['equity-curve', activeChallengeId],
    queryFn: () => statsApi.getEquityCurve(activeChallengeId!),
    enabled: !!activeChallengeId,
    refetchInterval: 30_000,
  })

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey: ['trade-history', activeChallengeId, filterSide, filterResult],
    queryFn: ({ pageParam }: { pageParam: number | undefined }) =>
      tradingApi.getHistory(activeChallengeId!, {
        cursor: pageParam,
        limit: 20,
        side: filterSide !== 'All' ? filterSide : undefined,
      }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: undefined as number | undefined,
    enabled: !!activeChallengeId,
  })

  const trades = (data?.pages.flatMap((p) => p.trades ?? []) ?? []).filter((t) => {
    if (!t) return false
    if (filterResult === 'Win') return (t.pnl ?? 0) > 0
    if (filterResult === 'Loss') return (t.pnl ?? 0) <= 0
    return true
  })

  const totalPnl = trades.reduce((s, t) => s + (t.pnl ?? 0), 0)
  const winCount = trades.filter((t) => (t.pnl ?? 0) > 0).length
  const winRate = trades.length > 0 ? (winCount / trades.length) * 100 : 0

  if (!activeChallengeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-8 text-center">
        <span className="text-5xl">📋</span>
        <h2 className="text-xl font-bold text-white">Нет активного испытания</h2>
        <p className="text-text-secondary">История пуста</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <h1 className="text-xl font-bold text-white">История сделок</h1>
      </div>

      {/* Equity chart */}
      {equityData.length > 1 && (
        <div className="mx-4 mb-4 glass-card p-3">
          <p className="text-xs text-text-secondary mb-2">Кривая капитала</p>
          <EquitySparkline data={equityData} height={80} />
        </div>
      )}

      {/* Summary stats */}
      {trades.length > 0 && (
        <div className="mx-4 mb-4 grid grid-cols-3 gap-2">
          <div className="glass-card p-3 text-center">
            <p className="text-xs text-text-secondary">Сделок</p>
            <p className="num font-bold text-white text-lg">{trades.length}</p>
          </div>
          <div className="glass-card p-3 text-center">
            <p className="text-xs text-text-secondary">Win Rate</p>
            <p className="num font-bold text-lg" style={{ color: winRate >= 50 ? '#00D4AA' : '#FF4757' }}>
              {winRate.toFixed(0)}%
            </p>
          </div>
          <div className="glass-card p-3 text-center">
            <p className="text-xs text-text-secondary">Итого P&L</p>
            <PnLNumber value={totalPnl} size="sm" />
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="px-4 mb-3 flex flex-col gap-2">
        {/* Side filter */}
        <div className="flex gap-1 p-1 bg-bg-border rounded-xl">
          {(['All', 'Buy', 'Sell'] as FilterSide[]).map((f) => (
            <button
              key={f}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: filterSide === f ? '#12121A' : 'transparent',
                color: filterSide === f
                  ? f === 'Buy' ? '#00D4AA' : f === 'Sell' ? '#FF4757' : '#fff'
                  : '#4A4A5A',
              }}
              onClick={() => setFilterSide(f)}
            >
              {f === 'All' ? 'Все' : f === 'Buy' ? '🟢 Лонг' : '🔴 Шорт'}
            </button>
          ))}
        </div>
        {/* Result filter */}
        <div className="flex gap-1 p-1 bg-bg-border rounded-xl">
          {(['All', 'Win', 'Loss'] as FilterResult[]).map((f) => (
            <button
              key={f}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: filterResult === f ? '#12121A' : 'transparent',
                color: filterResult === f
                  ? f === 'Win' ? '#00D4AA' : f === 'Loss' ? '#FF4757' : '#fff'
                  : '#4A4A5A',
              }}
              onClick={() => setFilterResult(f)}
            >
              {f === 'All' ? 'Все' : f === 'Win' ? 'Прибыль' : 'Убыток'}
            </button>
          ))}
        </div>
      </div>

      {/* Trade list */}
      <div className="px-4 space-y-2">
        {isLoading ? (
          <DashboardSkeleton />
        ) : trades.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-text-muted text-sm">Нет сделок по выбранным фильтрам</p>
          </div>
        ) : (
          <>
            {trades.map((trade, i) => (
              <TradeRow
                key={trade.trade_id ?? i}
                trade={trade}
                onShare={() => setShareVisible(trade)}
              />
            ))}
            {hasNextPage && (
              <button
                className="w-full py-3 rounded-xl text-sm text-text-secondary"
                style={{ background: '#1E1E2E' }}
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Загрузка...' : 'Загрузить ещё'}
              </button>
            )}
          </>
        )}
      </div>

      {/* Share PnL card overlay */}
      {shareVisible && (
        <SharePnLOverlay trade={shareVisible} onClose={() => setShareVisible(null)} />
      )}
    </div>
  )
}

function TradeRow({ trade, onShare }: { trade: TradeHistory; onShare: () => void }) {
  const isLong = trade.side === 'Buy'
  const isProfit = (trade.pnl ?? 0) > 0
  const dateStr = trade.closed_at ?? trade.created_at
  const date = dateStr ? new Date(dateStr) : new Date()

  return (
    <motion.div
      className="glass-card p-3"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded font-bold ${
              isLong ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'
            }`}
          >
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          <span className="text-sm font-semibold text-white">{trade.symbol}</span>
          <span className="num text-xs text-text-muted">{trade.qty}</span>
        </div>
        <PnLNumber value={trade.pnl} size="sm" />
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {trade.entry_price && (
            <span className="num text-xs text-text-muted">
              Вход: ${trade.entry_price.toFixed(2)}
            </span>
          )}
          {trade.exit_price && (
            <span className="num text-xs text-text-muted">
              Выход: ${trade.exit_price.toFixed(2)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">
            {date.toLocaleDateString('ru', { day: '2-digit', month: 'short' })}{' '}
            {date.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); onShare() }}
            className="text-xs px-2 py-0.5 rounded"
            style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
          >
            Поделиться
          </button>
        </div>
      </div>
    </motion.div>
  )
}

function SharePnLOverlay({ trade, onClose }: { trade: TradeHistory; onClose: () => void }) {
  const isLong = trade.side === 'Buy'
  const isProfit = (trade.pnl ?? 0) > 0

  return (
    <motion.div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-6"
      style={{ background: 'rgba(0,0,0,0.85)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onPointerUp={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <motion.div
        className="w-full max-w-sm rounded-3xl p-6 relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #12121A, #1E1E2E)',
          border: `1px solid ${isProfit ? '#00D4AA30' : '#FF475730'}`,
          boxShadow: `0 20px 60px ${isProfit ? 'rgba(0,212,170,0.2)' : 'rgba(255,71,87,0.2)'}`,
        }}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle at 50% 0%, ${isProfit ? '#00D4AA15' : '#FF475715'} 0%, transparent 70%)`,
          }}
        />
        <div className="relative z-10">
          <p className="text-text-muted text-xs mb-1 font-semibold tracking-widest uppercase">CHM KRYPTON</p>
          <div className="flex items-center gap-2 mb-4">
            <span className={`text-xs px-2 py-0.5 rounded font-bold ${isLong ? 'text-profit bg-profit/10' : 'text-loss bg-loss/10'}`}>
              {isLong ? 'LONG' : 'SHORT'}
            </span>
            <span className="font-bold text-white">{trade.symbol}</span>
          </div>
          <div className="text-center mb-4">
            <p className="text-4xl font-bold num" style={{ color: isProfit ? '#00D4AA' : '#FF4757' }}>
              {isProfit ? '+' : ''}{trade.pnl.toFixed(2)} USDT
            </p>
            {trade.pnl_pct !== undefined && (
              <p className="text-lg num mt-1" style={{ color: isProfit ? '#00D4AA80' : '#FF475780' }}>
                {isProfit ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
              </p>
            )}
          </div>
          {trade.entry_price && trade.exit_price && (
            <div className="flex justify-between text-sm text-text-secondary num mb-4">
              <span>Вход: ${trade.entry_price.toFixed(2)}</span>
              <span>Выход: ${trade.exit_price.toFixed(2)}</span>
            </div>
          )}
          <p className="text-center text-text-muted text-xs">t.me/chm_krypton</p>
        </div>
      </motion.div>
    </motion.div>
  )
}
