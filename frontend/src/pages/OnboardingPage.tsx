/**
 * OnboardingPage — 3-слайдовый онбординг для новых пользователей.
 */
import { ReactNode, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { FlaskIcon, DNAIcon, DiamondIcon } from '@/components/ui/Icon'

const SLIDE_ICONS: ReactNode[] = [
  <FlaskIcon size={96} color="#A855F7" />,
  <DNAIcon size={96} color="#3B82F6" />,
  <DiamondIcon size={96} color="#00D4AA" />,
]

const SLIDES = [
  {
    title: 'Что такое проп-трейдинг?',
    description:
      'Торгуй чужим капиталом — зарабатывай своё. CHM_KRYPTON выдаёт финансирование от $5K до $200K лучшим трейдерам.',
    gradient: 'from-purple-900/40 to-bg-primary',
  },
  {
    title: 'Путь Элемента',
    description:
      'Пройди путь от Isotope до Krypton. Каждый этап — это испытание, рост и новые возможности.',
    gradient: 'from-blue-900/40 to-bg-primary',
  },
  {
    title: 'До 90% от прибыли',
    description:
      'Получай до 90% прибыли с реального funded счёта. Масштабирование до $2,000,000.',
    gradient: 'from-teal-900/40 to-bg-primary',
  },
]

interface OnboardingPageProps {
  onComplete?: () => void
}

export function OnboardingPage({ onComplete }: OnboardingPageProps = {}) {
  const [current, setCurrent] = useState(0)
  const navigate = useNavigate()

  const goNext = () => {
    if (current < SLIDES.length - 1) {
      setCurrent(current + 1)
    } else if (onComplete) {
      onComplete()
    } else {
      navigate('/dashboard')
    }
  }

  const slide = SLIDES[current]

  return (
    <div
      className="min-h-dvh flex flex-col items-center justify-between px-6 pt-12 pb-10"
      style={{ background: '#0A0A0F' }}
      onClick={goNext}
    >
      {/* Background gradient */}
      <div
        className={`fixed inset-0 bg-gradient-to-b ${slide.gradient} pointer-events-none transition-all duration-700`}
      />

      {/* Logo */}
      <div className="relative text-center">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-2xl font-bold tracking-wider"
          style={{ color: '#6C63FF', letterSpacing: '0.15em' }}
        >
          CHM_KRYPTON
        </motion.div>
        <div className="text-text-muted text-xs mt-1">Trade Like an Element</div>
      </div>

      {/* Slide content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={current}
          initial={{ opacity: 0, x: 60 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -60 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="relative flex flex-col items-center text-center gap-6 flex-1 justify-center"
        >
          <motion.div
            className="flex items-center justify-center"
            animate={{ scale: [1, 1.08, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            {SLIDE_ICONS[current]}
          </motion.div>
          <div className="space-y-3 max-w-xs">
            <h2 className="text-2xl font-bold text-white">{slide.title}</h2>
            <p className="text-text-secondary leading-relaxed">{slide.description}</p>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Dots + Button */}
      <div className="relative w-full flex flex-col items-center gap-6">
        {/* Dots */}
        <div className="flex gap-2">
          {SLIDES.map((_, i) => (
            <motion.div
              key={i}
              className="rounded-full"
              animate={{
                width: i === current ? 24 : 6,
                background: i === current ? '#6C63FF' : '#2A2A3A',
              }}
              style={{ height: 6 }}
              transition={{ duration: 0.3 }}
              onClick={(e) => { e.stopPropagation(); setCurrent(i) }}
            />
          ))}
        </div>

        <motion.button
          className="w-full max-w-xs py-4 rounded-2xl font-bold text-white text-lg relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, #6C63FF, #00D4AA)' }}
          whileTap={{ scale: 0.97 }}
          onClick={(e) => { e.stopPropagation(); goNext() }}
        >
          <motion.div
            className="absolute inset-0 opacity-20"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }}
            animate={{ x: ['-100%', '200%'] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          />
          {current < SLIDES.length - 1 ? 'Далее' : 'Начать путь'}
        </motion.button>

        {current < SLIDES.length - 1 && (
          <button
            className="text-text-muted text-sm"
            onClick={(e) => { e.stopPropagation(); navigate('/dashboard') }}
          >
            Пропустить
          </button>
        )}
      </div>
    </div>
  )
}
