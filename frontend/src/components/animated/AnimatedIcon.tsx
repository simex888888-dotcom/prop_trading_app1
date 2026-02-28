/**
 * AnimatedIcon — Lottie анимация для достижений и иконок.
 * При prefers-reduced-motion показывает статичный PNG.
 */
import Lottie from 'lottie-react'
import { useEffect, useRef, useState } from 'react'

interface AnimatedIconProps {
  src: string        // путь к .lottie или URL
  staticSrc?: string // PNG fallback
  size?: number
  loop?: boolean
  autoplay?: boolean
  className?: string
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return reduced
}

export function AnimatedIcon({
  src,
  staticSrc,
  size = 48,
  loop = true,
  autoplay = true,
  className = '',
}: AnimatedIconProps) {
  const reducedMotion = useReducedMotion()
  const [animData, setAnimData] = useState<object | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (reducedMotion) return
    fetch(src)
      .then((r) => r.json())
      .then(setAnimData)
      .catch(() => setError(true))
  }, [src, reducedMotion])

  if (reducedMotion || error || !animData) {
    if (staticSrc) {
      return (
        <img
          src={staticSrc}
          alt=""
          width={size}
          height={size}
          className={className}
          style={{ width: size, height: size, objectFit: 'contain' }}
        />
      )
    }
    return <div style={{ width: size, height: size }} className={`bg-bg-border rounded-lg ${className}`} />
  }

  return (
    <Lottie
      animationData={animData}
      loop={loop}
      autoplay={autoplay}
      style={{ width: size, height: size }}
      className={className}
    />
  )
}
