/**
 * Checklist de envio de cada celular, visto pelo adulto no site. Os itens de ajuste do Android vêm do
 * próprio app (2.0.7+) junto com a posição; envio e internet o site calcula pela hora do último contato.
 * Sem React, para dar para testar sozinho.
 */

export interface ChecklistInformado {
  gps: boolean | null
  sempre: boolean | null
  precisa: boolean | null
  bateria_livre: boolean | null
  inicio_automatico: string | null
  inicio_automatico_em: string | null
}

export interface CelularParaChecklist {
  revogado: boolean
  atualizado_em: string | null
  visto_em: string | null
  checklist?: ChecklistInformado | null
  checklist_em?: string | null
}

/** ok: tudo certo · falta: precisa de ajuste · atrasado: parou de enviar · manual: só a pessoa confirmou · sem_dado: app antigo */
export type EstadoItemSite = 'ok' | 'falta' | 'atrasado' | 'manual' | 'manual_pendente' | 'sem_dado'

export interface ItemSite {
  chave: string
  nome: string
  estado: EstadoItemSite
  detalhe: string
}

export const ENVIO_ATRASADO_S = 30 * 60

export function duracao(segundos: number): string {
  const minutos = Math.floor(Math.max(0, segundos) / 60)
  if (minutos < 1) return 'menos de 1 min'
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 24) return minutos % 60 === 0 ? `${horas} h` : `${horas} h ${minutos % 60} min`
  const dias = Math.floor(horas / 24)
  return dias === 1 ? '1 dia' : `${dias} dias`
}

function dataBr(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

const SEM_DADO = 'O app deste celular ainda não informa este item. Atualize o app para a versão mais nova.'

function booleano(chave: string, nome: string, valor: boolean | null | undefined, falta: string, temChecklist: boolean): ItemSite {
  if (!temChecklist || valor == null) return { chave, nome, estado: 'sem_dado', detalhe: SEM_DADO }
  return valor ? { chave, nome, estado: 'ok', detalhe: '' } : { chave, nome, estado: 'falta', detalhe: falta }
}

/** Os mesmos itens da tela do app, na mesma ordem. agoraMs fica de fora para os testes. */
export function checklistDoCelular(celular: CelularParaChecklist, agoraMs: number = Date.now()): ItemSite[] {
  const c = celular.checklist ?? null
  const tem = c != null
  const segundosDesde = (iso: string | null) => (iso ? Math.floor((agoraMs - new Date(iso).getTime()) / 1000) : null)
  const itens: ItemSite[] = [
    booleano('gps', 'Localização do celular ligada', c?.gps, 'A localização do celular estava desligada.', tem),
    booleano('sempre', 'Localização "o tempo todo"', c?.sempre, 'Falta "Permitir o tempo todo": só envia com o app aberto.', tem),
    booleano('precisa', 'Precisão alta', c?.precisa, 'Localização aproximada ou GPS desligado: o "está em Casa" pode errar.', tem),
    booleano('bateria', 'Bateria do app sem restrição', c?.bateria_livre, 'O Android pode parar o envio para economizar bateria.', tem),
  ]

  const desdeEnvio = segundosDesde(celular.atualizado_em)
  if (desdeEnvio == null) {
    itens.push({ chave: 'envio', nome: 'Envio com o app fechado', estado: 'falta', detalhe: 'Ainda não enviou nenhuma localização.' })
  } else if (desdeEnvio > ENVIO_ATRASADO_S) {
    itens.push({
      chave: 'envio',
      nome: 'Envio com o app fechado',
      estado: 'atrasado',
      detalhe: `Último envio há ${duracao(desdeEnvio)}. O mapa mostra a última posição recebida, não a atual. Abra o app no celular e confira o checklist.`,
    })
  } else {
    itens.push({ chave: 'envio', nome: 'Envio com o app fechado', estado: 'ok', detalhe: `Último envio há ${duracao(desdeEnvio)}.` })
  }

  const auto = c?.inicio_automatico
  if (!tem || auto == null) {
    itens.push({ chave: 'inicio_automatico', nome: 'Início automático', estado: 'sem_dado', detalhe: SEM_DADO })
  } else if (auto === 'confirmado') {
    const quando = c?.inicio_automatico_em ? ` em ${dataBr(c.inicio_automatico_em)}` : ''
    itens.push({
      chave: 'inicio_automatico',
      nome: 'Início automático',
      estado: 'manual',
      detalhe: `Confirmado no celular${quando}. O Android não deixa o app conferir.`,
    })
  } else if (auto === 'pendente') {
    itens.push({
      chave: 'inicio_automatico',
      nome: 'Início automático',
      estado: 'manual_pendente',
      detalhe: 'Ainda não confirmado no celular. Nesta marca, sem isso o Android costuma parar o envio.',
    })
  }
  // "nao_se_aplica": a marca não tem essa chave; o item não aparece.

  const desdeContato = segundosDesde(celular.visto_em)
  if (desdeContato == null) {
    itens.push({ chave: 'rede', nome: 'Internet ligada', estado: 'sem_dado', detalhe: 'O celular ainda não falou com o site.' })
  } else if (desdeContato > ENVIO_ATRASADO_S) {
    itens.push({
      chave: 'rede',
      nome: 'Internet ligada',
      estado: 'atrasado',
      detalhe: `Sem contato com o site há ${duracao(desdeContato)}: sem internet, app parado ou celular desligado.`,
    })
  } else {
    itens.push({ chave: 'rede', nome: 'Internet ligada', estado: 'ok', detalhe: '' })
  }
  return itens
}

/** Itens que pedem ação (sem_dado não conta: é só app antigo). */
export function pendencias(itens: ItemSite[]): ItemSite[] {
  return itens.filter((item) => item.estado === 'falta' || item.estado === 'atrasado' || item.estado === 'manual_pendente')
}

/**
 * Linha de resumo do checklist. "Tudo certo" só quando o app informou os ajustes e nada pede ação:
 * celular com app antigo (sem checklist) ou com item sem dado nunca aparece como "tudo certo".
 */
export function resumoDoChecklist(itens: ItemSite[]): { texto: string; tom: 'ok' | 'alerta' | 'neutro' } {
  const faltam = pendencias(itens).length
  const semDado = itens.some((item) => item.estado === 'sem_dado')
  const pend = faltam === 1 ? '1 pendência' : `${faltam} pendências`
  if (faltam && semDado) return { texto: `Checklist de envio: ${pend}; ajustes sem dado (atualize o app para a versão mais nova)`, tom: 'alerta' }
  if (faltam) return { texto: `Checklist de envio: ${pend}`, tom: 'alerta' }
  if (semDado) return { texto: 'Checklist de envio: sem dado, atualize o app para a versão mais nova', tom: 'neutro' }
  return { texto: 'Checklist de envio: tudo certo', tom: 'ok' }
}
