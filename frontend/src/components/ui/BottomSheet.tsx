/**
 * BottomSheet — выдвижная нижняя панель с drag-жестом (свайп вниз закрывает).
 */
import { motion, AnimatePresence, useDragControls, useMotionValue, useTransform } from 'framer-motion'
import { ReactNode, useRef } from 'react'

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
  title?: string
  height?: string
}

export function BottomSheet({ isOpen, onClose, children, title, height = '70vh' }: BottomSheetProps) {
  const dragControls = useDragControls()
  const y = useMotionValue(0)

  // Backdrop opacity dims as sheet is dragged down
  const backdropOpacity = useTransform(y, [0, 200], [1, 0.2])

  function handleDragEnd(_: unknown, info: { offset: { y: number }; velocity: { y: number } }) {
    // Close if dragged down far enough or flicked fast enough
    if (info.offset.y > 120 || info.velocity.y > 500) {
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ opacity: backdropOpacity }}
            onPointerUp={(e) => { if (e.target === e.currentTarget) onClose() }}
          />

          {/* Sheet */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 bg-bg-secondary rounded-t-3xl z-50 flex flex-col"
            style={{ maxHeight: height, y }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            drag="y"
            dragControls={dragControls}
            dragListener={false}     // only the handle starts dragging
            dragConstraints={{ top: 0 }}
            dragElastic={{ top: 0.05, bottom: 0.3 }}
            onDragEnd={handleDragEnd}
          >
            {/* Drag handle — touch here to drag */}
            <div
              className="flex justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing shrink-0"
              onPointerDown={(e) => dragControls.start(e)}
              style={{ touchAction: 'none' }}
            >
              <div className="w-10 h-1 bg-bg-border rounded-full" />
            </div>

            {/* Header */}
            {title && (
              <div className="px-5 pb-4 border-b border-bg-border flex items-center justify-between shrink-0">
                <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary"
                  style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* Scrollable content */}
            <div
              className="overflow-y-auto flex-1"
              style={{ maxHeight: `calc(${height} - 80px)` }}
              // prevent drag from triggering while scrolling
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
