import { useState } from 'react'
import { Bell } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

function chaveParaBytes(chave: string) {
  const preenchida = chave + '='.repeat((4 - (chave.length % 4)) % 4)
  const bruto = atob(preenchida.replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(bruto, (caractere) => caractere.charCodeAt(0))
}

export default function LembreteCelular() {
  const user = useAuthStore((state) => state.user)
  const filho = !!user?.is_child
  const admin = !!user?.is_superuser
  const [mensagem, setMensagem] = useState('')
  const [erro, setErro] = useState('')
  const [ocupado, setOcupado] = useState(false)

  if (!filho && !admin) return null

  const ativar = async () => {
    setErro('')
    setMensagem('')
    setOcupado(true)
    try {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        throw new Error('Este navegador não recebe alerta com a página fechada.')
      }
      const permissao = await Notification.requestPermission()
      if (permissao !== 'granted') {
        throw new Error('O celular não autorizou o alerta.')
      }
      const registro = await navigator.serviceWorker.ready
      const existente = await registro.pushManager.getSubscription()
      if (existente) await existente.unsubscribe()
      const { data } = await api.get('/notificacoes/chave-publica')
      const inscricao = await registro.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: chaveParaBytes(data.publicKey),
      })
      const corpo = inscricao.toJSON()
      await api.post('/notificacoes/inscricao', {
        endpoint: corpo.endpoint,
        keys: corpo.keys,
      })
      setMensagem('Alertas ativados neste celular.')
    } catch (exc) {
      const texto = exc instanceof Error ? exc.message : ''
      if (texto.includes('push service')) {
        setErro('O Chrome não aceitou o alerta. Atualize a página e tente de novo.')
      } else {
        setErro(texto || 'Não foi possível ativar os alertas.')
      }
    } finally {
      setOcupado(false)
    }
  }

  const disparar = async () => {
    setErro('')
    setMensagem('')
    setOcupado(true)
    try {
      const { data } = await api.post('/notificacoes/lembretes/disparar')
      const partes = []
      if (data.enviados?.length) {
        partes.push(data.enviados.map((item: { filho: string; tarefas: string[] }) => `${item.filho}: ${item.tarefas.join(', ')}`).join(' · '))
      }
      if (data.sem_inscricao?.length) partes.push(`Sem alerta no celular: ${data.sem_inscricao.join(', ')}`)
      if (data.sem_tarefa?.length) partes.push(`Sem tarefa de hoje, amanhã ou atrasada: ${data.sem_tarefa.join(', ')}`)
      setMensagem(partes.join(' ') || 'Nenhum filho para avisar.')
    } catch (exc) {
      const detalhe = (exc as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErro(typeof detalhe === 'string' ? detalhe : 'Não foi possível disparar o alerta.')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3">
      <p className="text-sm text-amber-950">
        O alerta toca enquanto houver tarefa de hoje, de amanhã ou atrasada. O intervalo é o da família, só das 13h às 21h.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {filho && (
          <button type="button" onClick={ativar} disabled={ocupado} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-amber-600 px-3 text-sm font-medium text-white disabled:opacity-60">
            <Bell className="h-4 w-4" />
            Ativar alertas neste celular
          </button>
        )}
        {admin && (
          <button type="button" onClick={disparar} disabled={ocupado} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-amber-700 px-3 text-sm font-medium text-amber-900 disabled:opacity-60">
            Disparar lembrete agora
          </button>
        )}
      </div>
      {mensagem && <p className="mt-2 text-sm text-amber-950">{mensagem}</p>}
      {erro && <p className="mt-2 text-sm text-red-700">{erro}</p>}
    </div>
  )
}
