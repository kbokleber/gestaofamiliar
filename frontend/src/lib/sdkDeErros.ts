/**
 * Configuração do SDK. Importa só as funções usadas: gravação de tela (replay), formulário de
 * feedback e medição de desempenho nem entram no site. Carregado por monitoramento.ts, só com DSN.
 */
import {
  captureException, dedupeIntegration, globalHandlersIntegration, init, linkedErrorsIntegration, makeFetchTransport,
} from '@sentry/react'
import type { BrowserOptions, ErrorEvent as EventoDeErro } from '@sentry/react'
import { envelopeSoDeErro, filtrarEvento } from './filtroLgpd'

/** Scripts que a página carregou: os do HTML e os baixados depois (páginas sob demanda). */
function scriptsCarregados(): Set<string> {
  const doHtml = [...document.querySelectorAll<HTMLScriptElement | HTMLLinkElement>('script[src], link[rel="modulepreload"]')]
    .map((el) => (el instanceof HTMLScriptElement ? el.src : el.href))
  const baixados = performance.getEntriesByType('resource').map((r) => r.name)
  return new Set([...doHtml, ...baixados].map((endereco) => endereco.split(/[?#]/, 1)[0]))
}

export function ligarSdk(dsn: string, ambiente: string, versao: string): void {
  const opcoes: BrowserOptions = {
    dsn,
    environment: ambiente,
    release: `gf-site@${versao}`,
    // Só o necessário para pegar erros: sem histórico de cliques/chamadas, sem navegador, sem sessão.
    defaultIntegrations: false,
    integrations: [
      globalHandlersIntegration({ onerror: true, onunhandledrejection: true }),
      dedupeIntegration(),
      linkedErrorsIntegration(),
    ],
    sendDefaultPii: false,
    maxBreadcrumbs: 0,
    beforeBreadcrumb: () => null,
    beforeSend: (evento, dica) =>
      filtrarEvento(evento, {
        origem: window.location.origin, carregados: scriptsCarregados(), erro: dica.originalException,
      }) as EventoDeErro | null,
    beforeSendTransaction: () => null,
    enableLogs: false,
    beforeSendLog: () => null,
    sendClientReports: false,
    tracePropagationTargets: [],
    transport: (opcoesDoTransporte) => {
      const real = makeFetchTransport({
        ...opcoesDoTransporte,
        // Sem cookies e sem dizer de qual página veio.
        fetchOptions: { credentials: 'omit', referrerPolicy: 'no-referrer' },
      })
      return {
        ...real,
        send: (envelope) => {
          const seguro = envelopeSoDeErro(envelope)
          return seguro ? real.send(seguro as typeof envelope) : Promise.resolve({})
        },
      }
    },
  }
  init(opcoes)
}

export function enviarErro(erro: unknown): void {
  // Objeto que não é Error (ex.: resposta da API) não é enviado: só o fato de ter havido erro.
  captureException(erro instanceof Error ? erro : new Error('Erro sem tipo'))
}
