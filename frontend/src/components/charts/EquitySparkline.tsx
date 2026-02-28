/**
 * EquitySparkline — мини-график equity curve на дашборде.
 * Использует lightweight-charts TradingView.
 */
import { createChart, ColorType, LineStyle } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { EquityPoint } from '@/api/client'

interface EquitySparklineProps {
  data: EquityPoint[]
  height?: number
  className?: string
}

export function EquitySparkline({ data, height = 80, className = '' }: EquitySparklineProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null)

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'transparent',
      },
      grid: { horzLines: { visible: false }, vertLines: { visible: false } },
      crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      handleScroll: false,
      handleScale: false,
    })
    chartRef.current = chart

    const isProfit = data.length > 1 && data[data.length - 1].equity >= data[0].equity
    const lineColor = isProfit ? '#00D4AA' : '#FF4757'

    const lineSeries = chart.addLineSeries({
      color: lineColor,
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
    })

    const chartData = data.map((pt) => ({
      time: (pt.timestamp / 1000) as any,
      value: pt.equity,
    }))
    lineSeries.setData(chartData)
    chart.timeScale().fitContent()

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
  }, [data])

  if (data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center text-text-muted text-xs ${className}`}
        style={{ height }}
      >
        Нет данных
      </div>
    )
  }

  return <div ref={containerRef} style={{ height }} className={`w-full ${className}`} />
}
