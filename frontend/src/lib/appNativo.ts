/**
 * Ponte com o app Android do Gestão Familiar, quando o site está aberto dentro dele.
 * O app injeta `window.GFAppNativo` (JavascriptInterface) e marca o user agent com "GestaoFamiliarApp/".
 */
interface PonteNativa {
  salvarArquivo(base64: string, nome: string, tipo: string): void
  /** Informa ao app quem está logado (token vazio = saiu), para ele ligar localização ou alertas. */
  sessao?(token: string, usuarioJson: string): void
  /** App 2.0.5+: abre a tela nativa "Configurações de envio" do próprio celular. */
  abrirConfiguracoesDeEnvio?(): void
}

declare global {
  interface Window {
    GFAppNativo?: PonteNativa
  }
}

export function dentroDoApp(): boolean {
  return typeof navigator !== 'undefined' && navigator.userAgent.includes('GestaoFamiliarApp/')
}

/** Versão do app Android (ex.: "2.0.2"), lida do user agent que o app marca. Fora do app, null. */
export function versaoDoApp(): string | null {
  if (typeof navigator === 'undefined') return null
  const achada = navigator.userAgent.match(/GestaoFamiliarApp\/([0-9][0-9A-Za-z.\-]*)/)
  return achada ? achada[1] : null
}

export function ponteNativa(): PonteNativa | null {
  return typeof window !== 'undefined' && window.GFAppNativo ? window.GFAppNativo : null
}

/** Converte o arquivo para base64 (sem o prefixo data:) para entregar ao app. */
export function blobParaBase64(conteudo: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const leitor = new FileReader()
    leitor.onload = () => resolve(String(leitor.result).split(',', 2)[1] ?? '')
    leitor.onerror = () => reject(leitor.error)
    leitor.readAsDataURL(conteudo)
  })
}

/** Avisa o app sempre que o login muda. Sem o app, não faz nada. */
export function avisarSessaoAoApp(
  token: string | null,
  usuario: { id: number; first_name?: string; username: string; is_child?: boolean; family_id?: number | null } | null,
): void {
  const ponte = ponteNativa()
  if (!ponte?.sessao) return
  try {
    if (!token || !usuario) {
      ponte.sessao('', '')
      return
    }
    ponte.sessao(token, JSON.stringify({
      id: usuario.id,
      nome: (usuario.first_name || '').trim() || usuario.username,
      is_child: !!usuario.is_child,
      family_id: usuario.family_id ?? null,
    }))
  } catch {
    // a ponte nunca pode quebrar o site
  }
}
