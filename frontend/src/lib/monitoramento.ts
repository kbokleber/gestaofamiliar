/**
 * Erros do site para o GlitchTip (logs.kbosolucoes.com.br), sem dados pessoais (veja filtroLgpd.ts).
 * O DSN entra na compilação (VITE_GF_SENTRY_DSN_SITE). Vazio: o SDK não é carregado nem compilado.
 */
import { APP_VERSION } from '../config/version'

type Sdk = typeof import('./sdkDeErros')

let carregando: Promise<Sdk | null> | null = null

/** Liga uma vez só. Devolve false quando não há DSN. */
export function iniciarMonitoramento(): boolean {
  if (!import.meta.env.VITE_GF_SENTRY_DSN_SITE) return false
  const dsn = import.meta.env.VITE_GF_SENTRY_DSN_SITE.trim()
  if (!dsn) return false
  carregando ??= import('./sdkDeErros')
    .then((sdk) => {
      sdk.ligarSdk(dsn, import.meta.env.MODE, APP_VERSION)
      return sdk
    })
    .catch(() => null) // o monitoramento nunca pode derrubar o site
  return true
}

/** Para erros que o site já trata (tela de erro, falha no login). Desligado: não faz nada. */
export function capturarErro(erro: unknown): void {
  if (!carregando) return
  void carregando.then((sdk) => sdk?.enviarErro(erro)).catch(() => undefined)
}
