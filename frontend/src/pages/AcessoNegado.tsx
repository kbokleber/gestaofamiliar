import { keycloakEnabled, logoutKeycloak } from '../lib/keycloak'
import { useAuthStore } from '../stores/authStore'

const BLOCKED_KEY = 'auth-blocked'

export function readBlockedMessage() {
  return sessionStorage.getItem(BLOCKED_KEY) || 'Acesso negado.'
}

export function rememberBlockedMessage(message: string) {
  sessionStorage.setItem(BLOCKED_KEY, message)
}

export function clearBlockedMessage() {
  sessionStorage.removeItem(BLOCKED_KEY)
}

export default function AcessoNegado() {
  const logout = useAuthStore((state) => state.logout)
  const message = readBlockedMessage()

  const handleLogout = () => {
    clearBlockedMessage()
    logout()
    if (keycloakEnabled) {
      logoutKeycloak()
      return
    }
    window.location.href = '/login'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white shadow rounded-lg p-6 space-y-4">
        <h1 className="text-xl font-semibold text-gray-900">Acesso negado</h1>
        <p className="text-sm text-gray-700">{message}</p>
        <button
          type="button"
          onClick={handleLogout}
          className="w-full py-2 px-4 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          Sair
        </button>
      </div>
    </div>
  )
}
