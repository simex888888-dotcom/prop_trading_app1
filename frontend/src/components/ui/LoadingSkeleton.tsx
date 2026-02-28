/**
 * LoadingSkeleton — анимированный скелетон для загрузки.
 */
import { motion } from 'framer-motion'

interface SkeletonProps {
  className?: string
  height?: string | number
  rounded?: string
}

export function Skeleton({ className = '', height = 16, rounded = 'rounded-lg' }: SkeletonProps) {
  return (
    <motion.div
      className={`bg-bg-border ${rounded} ${className}`}
      style={{ height }}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="glass-card p-5 space-y-3">
      <Skeleton height={20} className="w-1/3" />
      <Skeleton height={40} className="w-2/3" />
      <Skeleton height={16} className="w-full" />
      <Skeleton height={16} className="w-4/5" />
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-4 px-4">
      <CardSkeleton />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton height={80} />
        <Skeleton height={80} />
      </div>
      <Skeleton height={120} />
    </div>
  )
}
