/**
 * BottomSheet — выдвижная нижняя панель с анимацией.
 */
import { motion, AnimatePresence } from 'framer-motion'
import { ReactNode } from 'react'

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
  title?: string
  height?: string
}

export function BottomSheet({ isOpen, onClose, children, title, height = '70vh' }: BottomSheetProps) {
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
            onClick={onClose}
          />
          {/* Sheet */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 bg-bg-secondary rounded-t-3xl z-50 overflow-hidden"
            style={{ maxHeight: height }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 bg-bg-border rounded-full" />
            </div>
            {title && (
              <div className="px-5 pb-4 border-b border-bg-border">
                <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
              </div>
            )}
            <div className="overflow-y-auto" style={{ maxHeight: `calc(${height} - 80px)` }}>
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
