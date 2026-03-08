/**
 * BottomSheet — выдвижная нижняя панель.
 * Свайп вниз за ручку — закрывает. dragSnapToOrigin — пружинный возврат.
 */
import { motion, AnimatePresence, useDragControls } from 'framer-motion'
import { ReactNode } from 'react'

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
  title?: string
  /** CSS height, e.g. '85vh' or '560px'. Default '85vh'. */
  height?: string
}

export function BottomSheet({
  isOpen,
  onClose,
  children,
  title,
  height = '85vh',
}: BottomSheetProps) {
  const dragControls = useDragControls()

  function handleDragEnd(
    _: unknown,
    info: { offset: { y: number }; velocity: { y: number } },
  ) {
    if (info.offset.y > 90 || info.velocity.y > 350) {
      onClose()
    }
    // dragSnapToOrigin handles automatic spring-back for partial drags
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            onPointerUp={(e) => {
              if (e.target === e.currentTarget) onClose()
            }}
          />

          {/* Sheet */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 flex flex-col rounded-t-3xl"
            style={{
              background: '#13131F',
              height,
              maxHeight: '94vh',
              boxShadow: '0 -8px 48px rgba(0,0,0,0.6)',
            }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            drag="y"
            dragControls={dragControls}
            dragListener={false}
            dragConstraints={{ top: 0 }}
            dragSnapToOrigin
            dragElastic={{ top: 0, bottom: 0.45 }}
            onDragEnd={handleDragEnd}
          >
            {/* ── Drag handle (full-width touch target) ── */}
            <div
              className="w-full flex flex-col items-center pt-3 pb-1 shrink-0 select-none"
              style={{ touchAction: 'none', cursor: 'grab' }}
              onPointerDown={(e) => dragControls.start(e)}
            >
              <div
                className="rounded-full"
                style={{ width: 40, height: 4, background: 'rgba(255,255,255,0.18)' }}
              />
            </div>

            {/* ── Header (optional) ── */}
            {title && (
              <div
                className="flex items-center justify-between px-5 pb-4 shrink-0"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
              >
                <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
                <button
                  onClick={onClose}
                  className="flex items-center justify-center rounded-full text-sm font-semibold"
                  style={{
                    width: 30,
                    height: 30,
                    background: 'rgba(255,255,255,0.07)',
                    color: 'rgba(255,255,255,0.5)',
                  }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* ── Scrollable content ── */}
            <div
              className="flex-1 overflow-y-auto overscroll-contain"
              /* Stop pointerDown from hitting the drag handler above */
              onPointerDown={(e) => e.stopPropagation()}
            >
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
