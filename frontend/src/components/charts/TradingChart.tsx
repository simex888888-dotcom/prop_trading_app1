/**
 * TradingChart — полноценный свечной график для терминала.
 * lightweight-charts TradingView + таймфреймы + индикаторы.
 */
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts'
import { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import type { KlineBar } from '@/api/client'

const TIMEFRAMES = [
  { label: '1m', value: '1' },
  { label: '5m', value: '5' },
  { label: '15m', value: '15' },
  { label: '1h', value: '60' },
  { label: '4h', value: '240' },
  { label: '1D', value: 'D' },
]

interface TradingChartProps {
  data: KlineBar[]
  symbol: string
  onTimeframeChange: (tf: string) => void
  activeTimeframe?: string
  height?: number
}

export function TradingChart({
  data,
  symbol,
  onTimeframeChange,
  activeTimeframe = '60',
  height = 320,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candleSeriesRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8B8B9A',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        horzLines: { color: 'rgba(30, 30, 46, 0.8)', style: LineStyle.Dotted },
        vertLines: { color: 'rgba(30, 30, 46, 0.8)', style: LineStyle.Dotted },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: '#1E1E2E',
        textColor: '#8B8B9A',
      },
      timeScale: {
        borderColor: '#1E1E2E',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { mouseWheel: true, pinch: true },
    })
    chartRef.current = chart

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00D4AA',
      downColor: '#FF4757',
      borderUpColor: '#00D4AA',
      borderDownColor: '#FF4757',
      wickUpColor: '#00D4AA',
      wickDownColor: '#FF4757',
    })
    candleSeriesRef.current = candleSeries

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    if (containerRef.current) observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (!candleSeriesRef.current || data.length === 0) return
    const chartData = data.map((bar) => ({
      time: bar.time as any,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }))
    candleSeriesRef.current.setData(chartData)
    chartRef.current?.timeScale().fitContent()
  }, [data])

  return (
    <div className="w-full flex flex-col" style={{ height }}>
      {/* Timeframe selector */}
      <div className="flex items-center gap-1 px-3 py-2 overflow-x-auto no-scrollbar">
        {TIMEFRAMES.map((tf) => (
          <motion.button
            key={tf.value}
            className="px-3 py-1 rounded-lg text-xs font-semibold shrink-0 num"
            style={{
              background: activeTimeframe === tf.value
                ? 'rgba(108, 99, 255, 0.3)'
                : 'transparent',
              color: activeTimeframe === tf.value ? '#6C63FF' : '#4A4A5A',
              border: activeTimeframe === tf.value
                ? '1px solid rgba(108, 99, 255, 0.4)'
                : '1px solid transparent',
            }}
            onClick={() => onTimeframeChange(tf.value)}
            whileTap={{ scale: 0.95 }}
          >
            {tf.label}
          </motion.button>
        ))}
      </div>

      {/* Chart */}
      <div
        ref={containerRef}
        className="flex-1 w-full"
        style={{ minHeight: 0 }}
      />
    </div>
  )
}
