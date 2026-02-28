/**
 * RiskMeter — круговой индикатор текущего риска.
 */
import { motion } from 'framer-motion'

interface RiskMeterProps {
  value: number    // 0-100
  size?: number
  label?: string
  colorOverride?: string
}

export function RiskMeter({ value, size = 80, label, colorOverride }: RiskMeterProps) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const pct = Math.min(100, Math.max(0, value))
  const dashOffset = circumference * (1 - pct / 100)

  const color = colorOverride ?? (
    pct >= 80 ? '#FF4757' :
    pct >= 60 ? '#FFA502' :
    '#00D4AA'
  )

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)' }}
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1E1E2E"
          strokeWidth={6}
        />
        {/* Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={circumference}
          animate={{ strokeDashoffset: dashOffset }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 6px ${color}80)` }}
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-xs font-semibold" style={{ color }}>
          {pct.toFixed(0)}%
        </span>
        {label && (
          <span className="text-text-secondary" style={{ fontSize: 8 }}>
            {label}
          </span>
        )}
      </div>
    </div>
  )
}
