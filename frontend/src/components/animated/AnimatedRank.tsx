/**
 * AnimatedRank — WebM видео ранга с прозрачностью.
 * Isotope → Reagent → Catalyst → Molecule → Crystal → Nucleus → Krypton
 */
import { useEffect, useRef } from 'react'

export type RankName = 'isotope' | 'reagent' | 'catalyst' | 'molecule' | 'crystal' | 'nucleus' | 'krypton'

const RANK_LABELS: Record<RankName, string> = {
  isotope: 'Isotope',
  reagent: 'Reagent',
  catalyst: 'Catalyst',
  molecule: 'Molecule',
  crystal: 'Crystal',
  nucleus: 'Nucleus',
  krypton: 'Krypton',
}

const RANK_COLORS: Record<RankName, string> = {
  isotope: '#8B8B9A',
  reagent: '#6C63FF',
  catalyst: '#A855F7',
  molecule: '#3B82F6',
  crystal: '#00D4AA',
  nucleus: '#FFA502',
  krypton: '#FFD700',
}

interface AnimatedRankProps {
  rank: RankName
  size?: number
  showLabel?: boolean
  className?: string
}

export function AnimatedRank({ rank, size = 64, showLabel = true, className = '' }: AnimatedRankProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (videoRef.current && !reducedMotion) {
      videoRef.current.playbackRate = 0.8
    }
  }, [reducedMotion])

  const color = RANK_COLORS[rank]
  const label = RANK_LABELS[rank]

  return (
    <div className={`flex flex-col items-center gap-1 ${className}`}>
      <div
        className="relative flex items-center justify-center rounded-full"
        style={{
          width: size,
          height: size,
          background: `radial-gradient(circle, ${color}20 0%, transparent 70%)`,
          boxShadow: `0 0 20px ${color}40`,
        }}
      >
        {reducedMotion ? (
          /* Статичный placeholder */
          <div
            className="rounded-full flex items-center justify-center text-lg font-bold"
            style={{
              width: size * 0.75,
              height: size * 0.75,
              background: `linear-gradient(135deg, ${color}40, ${color}10)`,
              color,
              border: `2px solid ${color}60`,
            }}
          >
            {label[0]}
          </div>
        ) : (
          <video
            ref={videoRef}
            src={`/assets/ranks/${rank}.webm`}
            autoPlay
            loop
            muted
            playsInline
            style={{ width: size * 0.85, height: size * 0.85, objectFit: 'contain' }}
            onError={(e) => {
              // Fallback если файл не найден
              const target = e.currentTarget
              target.style.display = 'none'
            }}
          />
        )}
      </div>
      {showLabel && (
        <span className="text-xs font-semibold tracking-wider uppercase" style={{ color }}>
          {label}
        </span>
      )}
    </div>
  )
}

/** Определяет ранг по количеству пройденных испытаний / total_pnl */
export function getRankByStats(fundedChallengesCount: number, totalPnl: number): RankName {
  if (totalPnl >= 200_000) return 'krypton'
  if (totalPnl >= 50_000) return 'nucleus'
  if (totalPnl >= 20_000 || fundedChallengesCount >= 3) return 'crystal'
  if (totalPnl >= 5_000 || fundedChallengesCount >= 2) return 'molecule'
  if (totalPnl >= 1_000 || fundedChallengesCount >= 1) return 'catalyst'
  if (totalPnl > 0) return 'reagent'
  return 'isotope'
}
