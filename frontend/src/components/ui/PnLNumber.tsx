/**
 * PnLNumber — анимированное число PnL с цветом.
 * Зелёный для прибыли, красный для убытка.
 * Использует JetBrains Mono для монопространственного вывода.
 */
import { motion, AnimatePresence } from 'framer-motion'
import { useRef, useEffect } from 'react'

interface PnLNumberProps {
  value: number
  prefix?: string
  suffix?: string
  decimals?: number
  showSign?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const SIZE_CLASSES = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-xl',
  xl: 'text-3xl font-semibold',
}

export function PnLNumber({
  value,
  prefix = '$',
  suffix = '',
  decimals = 2,
  showSign = true,
  size = 'md',
  className = '',
}: PnLNumberProps) {
  const isPositive = value >= 0
  const isZero = value === 0
  const prevValue = useRef(value)
  const changed = prevValue.current !== value

  useEffect(() => {
    prevValue.current = value
  }, [value])

  const colorClass = isZero
    ? 'text-text-secondary'
    : isPositive
    ? 'text-profit'
    : 'text-loss'

  const sign = showSign && !isZero ? (isPositive ? '+' : '') : ''
  const formatted = `${sign}${prefix}${Math.abs(value).toFixed(decimals)}${suffix}`

  return (
    <motion.span
      key={value}
      initial={changed ? { opacity: 0.5, y: -4 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`num font-medium ${colorClass} ${SIZE_CLASSES[size]} ${className}`}
    >
      {formatted}
    </motion.span>
  )
}
