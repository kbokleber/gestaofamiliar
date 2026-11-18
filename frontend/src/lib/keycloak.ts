import Keycloak from 'keycloak-js'
import { dentroDoApp } from './appNativo'

const url = import.meta.env.VITE_KEYCLOAK_URL
const realm = import.meta.env.VITE_KEYCLOAK_REALM
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID

export const keycloakEnabled = Boolean(url && realm && clientId)

export const keycloak: Keycloak | null = keycloakEnabled
  ? new Keycloak({ url: url!, realm: realm!, clientId: clientId! })
  : null

let initPromise: Promise<boolean> | null = null

/**
 * Dentro do app Android o login volta por /app-login: quando o login é pelo Google, ele acontece no
 * navegador do celular (o Google não deixa entrar dentro de apps) e essa página devolve o resultado ao app.
 */
export const CAMINHO_RETORNO_APP = '/app-login'
const SESSAO_APP = 'gf-app-sessao'

interface SessaoGuardada {
  token: string
  refreshToken: string
  idToken?: string
}

/** No app, a sessão fica guardada (área privada do app) para não pedir login toda vez que ele abre. */
function lerSessaoDoApp(): SessaoGuardada | null {
  try {
    const dados = JSON.parse(window.localStorage.getItem(SESSAO_APP) || 'null') as SessaoGuardada | null
    return dados?.token && dados.refreshToken ? dados : null
  } catch {
    return null
  }
}

function guardarSessaoDoApp() {
  if (!keycloak?.token || !keycloak.refreshToken) return
  try {
    window.localStorage.setItem(SESSAO_APP, JSON.stringify({
      token: keycloak.token,
      refreshToken: keycloak.refreshToken,
      idToken: keycloak.idToken,
    }))
  } catch {
    // sem espaço ou armazenamento bloqueado: só pede login de novo na próxima vez
  }
}

export function esquecerSessaoDoApp() {
  try {
    window.localStorage.removeItem(SESSAO_APP)
  } catch {
    // nada a fazer
  }
}

export function initKeycloak(): Promise<boolean> {
  if (!keycloak) {
    return Promise.resolve(false)
  }
  if (!initPromise) {
    const noApp = dentroDoApp()
    const guardada = noApp ? lerSessaoDoApp() : null
    if (noApp) {
      keycloak.onAuthSuccess = guardarSessaoDoApp
      keycloak.onAuthRefreshSuccess = guardarSessaoDoApp
      keycloak.onAuthRefreshError = esquecerSessaoDoApp
      keycloak.onAuthLogout = esquecerSessaoDoApp
    }
    initPromise = keycloak.init({
      onLoad: 'login-required',
      pkceMethod: 'S256',
      checkLoginIframe: false,
      ...(noApp ? { redirectUri: `${window.location.origin}${CAMINHO_RETORNO_APP}` } : {}),
      ...(guardada ? { token: guardada.token, refreshToken: guardada.refreshToken, idToken: guardada.idToken } : {}),
    })
  }
  return initPromise
}

export async function getAccessToken(): Promise<string | null> {
  if (!keycloak?.authenticated) {
    return null
  }
  try {
    await keycloak.updateToken(30)
  } catch {
    return null
  }
  return keycloak.token ?? null
}

export function logoutKeycloak() {
  if (!keycloak) {
    return
  }
  const redirectUri = `${window.location.origin}/`
  esquecerSessaoDoApp()
  void keycloak.logout({ redirectUri })
}
