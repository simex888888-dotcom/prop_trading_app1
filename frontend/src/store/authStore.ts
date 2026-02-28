/**
 * Zustand store для аутентификации.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  userId: number | null
  role: string | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  setUser: (userId: number, role: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      userId: null,
      role: null,
      isAuthenticated: false,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),

      setUser: (userId, role) => set({ userId, role }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          userId: null,
          role: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'chm-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        userId: state.userId,
        role: state.role,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
