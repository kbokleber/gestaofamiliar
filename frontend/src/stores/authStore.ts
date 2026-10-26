import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { keycloakEnabled } from '../lib/keycloak'

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  family_id?: number | null
  family_ids?: number[]
  is_superuser?: boolean
  is_staff?: boolean
  is_child?: boolean
  is_active?: boolean
  allowed_menus?: string[] | null
  api_token?: string | null
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) =>
        keycloakEnabled
          ? { user: null, token: null, isAuthenticated: false }
          : {
              user: state.user,
              token: state.token,
              isAuthenticated: state.isAuthenticated,
            },
    }
  )
)

