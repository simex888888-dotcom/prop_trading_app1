/**
 * App.tsx — главный роутер CHM_KRYPTON Mini App.
 */
import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'

import { authApi } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { useAppStore } from '@/store/appStore'
import { AnimatedTabBar } from '@/components/animated/AnimatedTabBar'
import { StatusOverlay, type StatusType } from '@/components/animated/StatusOverlay'

import { OnboardingPage } from '@/pages/OnboardingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ChallengesPage } from '@/pages/ChallengesPage'
import { TerminalPage } from '@/pages/TerminalPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { RulesPage } from '@/pages/RulesPage'
import { PayoutsPage } from '@/pages/PayoutsPage'
import { ScalingPage } from '@/pages/ScalingPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
    },
  },
})

// Pages with bottom tab bar
const TAB_PATHS = ['/dashboard', '/terminal', '/challenges', '/history', '/profile']

function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -12 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
        className="flex-1 overflow-y-auto"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

function AppLayout() {
  const location = useLocation()
  const showTabBar = TAB_PATHS.some((p) => location.pathname.startsWith(p))

  return (
    <div className="flex flex-col h-dvh overflow-hidden bg-bg-primary">
      <PageTransition>
        <Routes location={location}>
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/terminal" element={<TerminalPage />} />
          <Route path="/challenges" element={<ChallengesPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/payouts" element={<PayoutsPage />} />
          <Route path="/scaling" element={<ScalingPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </PageTransition>
      {showTabBar && <AnimatedTabBar />}
    </div>
  )
}

function AuthGate() {
  const setTokens = useAuthStore((s) => s.setTokens)
  const accessToken = useAuthStore((s) => s.accessToken)
  const setActiveChallenge = useAppStore((s) => s.setActiveChallenge)

  const [status, setStatus] = useState<'loading' | 'onboarding' | 'ready' | 'error'>('loading')
  const [statusOverlay, setStatusOverlay] = useState<StatusType | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    async function init() {
      try {
        // Get Telegram WebApp initData
        const tg = (window as any).Telegram?.WebApp
        const initData: string = tg?.initData ?? ''

        if (!initData && import.meta.env.DEV) {
          // Dev mode: skip real Telegram auth if no initData
          if (!accessToken) {
            setStatus('onboarding')
          } else {
            setStatus('ready')
          }
          return
        }

        // Expand Telegram WebApp to full screen
        tg?.expand()
        tg?.enableClosingConfirmation()
        tg?.setHeaderColor('#0A0A0F')
        tg?.setBackgroundColor('#0A0A0F')

        // Authenticate with backend
        const result = await authApi.loginTelegram(initData)
        setTokens(result.access_token, result.refresh_token)

        if (result.is_new) {
          setStatus('onboarding')
        } else {
          setStatus('ready')
        }
      } catch (e: any) {
        setErrorMsg(e?.response?.data?.detail ?? e?.message ?? 'Ошибка авторизации')
        setStatus('error')
      }
    }

    init()
  }, [])

  if (status === 'loading') {
    return (
      <div className="fixed inset-0 flex flex-col items-center justify-center bg-bg-primary gap-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 rounded-full border-2 border-brand-primary border-t-transparent"
        />
        <p className="text-text-secondary text-sm">Загрузка CHM KRYPTON...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="fixed inset-0 flex flex-col items-center justify-center bg-bg-primary gap-4 px-8 text-center">
        <span className="text-5xl">🔒</span>
        <h2 className="text-xl font-bold text-white">Ошибка доступа</h2>
        <p className="text-text-secondary text-sm">{errorMsg}</p>
        <button
          className="px-6 py-3 rounded-2xl font-bold text-white"
          style={{ background: 'linear-gradient(135deg, #6C63FF, #5A52E0)' }}
          onClick={() => window.location.reload()}
        >
          Повторить
        </button>
      </div>
    )
  }

  if (status === 'onboarding') {
    return <OnboardingPage onComplete={() => setStatus('ready')} />
  }

  return (
    <>
      <AppLayout />
      <StatusOverlay type={statusOverlay} onComplete={() => setStatusOverlay(null)} />
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthGate />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
