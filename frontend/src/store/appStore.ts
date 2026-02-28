/**
 * Zustand store для состояния приложения.
 */
import { create } from 'zustand'
import type { UserChallenge } from '@/api/client'

interface AppState {
  activeChallenge: UserChallenge | null
  activeChallengeId: number | null
  selectedPair: string
  isLoading: boolean
  setActiveChallenge: (challenge: UserChallenge | null) => void
  setSelectedPair: (pair: string) => void
  setLoading: (loading: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeChallenge: null,
  activeChallengeId: null,
  selectedPair: 'BTCUSDT',
  isLoading: false,

  setActiveChallenge: (challenge) =>
    set({
      activeChallenge: challenge,
      activeChallengeId: challenge?.id ?? null,
    }),

  setSelectedPair: (pair) => set({ selectedPair: pair }),
  setLoading: (loading) => set({ isLoading: loading }),
}))
