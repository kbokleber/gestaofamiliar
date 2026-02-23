import { useState, useEffect } from 'react'
import { Clock, Plus, Edit2, Trash2, Save, Filter, FileSpreadsheet, ArrowLeft, Paperclip } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
import Loading from '../../components/Loading'
import { toDateInputValue, formatDateFullBR } from '../../utils/dateUtils'
import { exportToExcel } from '../../utils/excelUtils'

interface Equipment {
  id: number
  name: string
}

interface MaintenanceOrder {
  id: number
  equipment_id: number
  equipment_name?: string | null  // Nome do equipamento (vindo da API para evitar "Desconhecido")
  title: string
  description: string
  status: string
  priority: string
  service_provider: string
  completion_date: string | null
  cost: number | null
  warranty_expiration: string | null
  warranty_terms: string
  invoice_number: string
  notes: string
  documents?: string | null  // JSON string com array de documentos
  has_documents?: boolean     // Indica se existem documentos
  created_at: string
  updated_at: string
}

const STATUS_OPTIONS = [
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'EM_ANDAMENTO', label: 'Em Andamento' },
  { value: 'CONCLUIDA', label: 'Concluída' },
  { value: 'CANCELADA', label: 'Cancelada' }
]

export default function MaintenanceOrders() {
  const queryClient = useQueryClient()
  const [filteredOrders, setFilteredOrders] = useState<MaintenanceOrder[]>([])
  const [viewMode, setViewMode] = useState<'list' | 'create'>('list')
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingOrder, setEditingOrder] = useState<MaintenanceOrder | null>(null)
  const [filters, setFilters] = useState({
    equipment_id: 0,
    start_date: '',
    end_date: ''
  })
  const [formData, setFormData] = useState({
    equipment_id: 0,
    title: '', // Título será gerado automaticamente ou pode ser a descrição
    description: '',
    status: 'PENDENTE',
    priority: 'MEDIA',
    service_provider: '',
    completion_date: '',
    cost: '',
    warranty_expiration: '',
    warranty_terms: '',
    invoice_number: '',
    notes: ''
  })
  const [documents, setDocuments] = useState<Document[]>([])

  // Carregar dados do localStorage como placeholder
  const getPlaceholderOrders = (): MaintenanceOrder[] | undefined => {
    try {
      const cached = localStorage.getItem('maintenance-orders-cache')
      return cached ? JSON.parse(cached) : undefined
    } catch {
      return undefined
    }
  }

  const getPlaceholderEquipment = (): Equipment[] | undefined => {
    try {
      const cached = localStorage.getItem('maintenance-equipment-cache')
      return cached ? JSON.parse(cached) : undefined
    } catch {
      return undefined
    }
  }

  // Primeira query: carregar ordens SEM documentos (rápido)
  const { data: orders = [], isLoading: loading, error: ordersError } = useQuery<MaintenanceOrder[]>({
    queryKey: ['maintenance-orders'],
    queryFn: async () => {
      // Carregar sem documentos para ser mais rápido
      const response = await api.get('/maintenance/orders', { params: { include_documents: false } })
      // Salvar apenas dados essenciais no cache (sem campos grandes)
      try {
        const cacheData = response.data.map((o: MaintenanceOrder) => ({
          id: o.id, equipment_id: o.equipment_id, equipment_name: o.equipment_name ?? null,
          title: o.title, status: o.status, priority: o.priority, completion_date: o.completion_date
        }))
        localStorage.setItem('maintenance-orders-cache', JSON.stringify(cacheData))
      } catch { /* localStorage cheio, ignorar */ }
      return response.data
    },
    placeholderData: getPlaceholderOrders(),
    staleTime: 5 * 60 * 1000,
  })

  const { data: equipment = [], isLoading: equipmentLoading, error: equipmentError } = useQuery<Equipment[]>({
    queryKey: ['maintenance-equipment'],
    queryFn: async () => {
      // Carregar sem documentos para ser mais rápido
      const response = await api.get('/maintenance/equipment', { params: { include_documents: false } })
      const data = Array.isArray(response.data) ? response.data : []
      try {
        const cacheData = data.map((e: any) => ({ id: e.id, name: e.name || String(e.id) }))
        localStorage.setItem('maintenance-equipment-cache', JSON.stringify(cacheData))
      } catch { /* localStorage cheio, ignorar */ }
      return data
    },
    placeholderData: getPlaceholderEquipment(),
    staleTime: 5 * 60 * 1000,
  })

  // Lista de opções do select: inclui equipamento atual ao editar (para exibir mesmo antes da lista carregar)
  const equipmentOptions: Equipment[] = (() => {
    const list = equipment.map((e: any) => ({ id: Number(e.id), name: e.name || `Equipamento #${e.id}` }))
    const currentId = formData.equipment_id
    if (currentId && !list.some((e) => e.id === currentId)) {
      return [{ id: currentId, name: `Equipamento #${currentId}` }, ...list]
    }
    return list
  })()

  // Opções do filtro por equipamento: derivadas das ordens (sempre preenchidas, não dependem da API de equipamentos)
  const filterEquipmentOptions: Equipment[] = (() => {
    const seen = new Set<number>()
    const list: Equipment[] = []
    for (const order of orders) {
      const id = Number(order.equipment_id)
      if (id && !seen.has(id)) {
        seen.add(id)
        list.push({
          id,
          name: order.equipment_name || `Equipamento #${id}`
        })
      }
    }
    return list.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
  })()

  const error = ordersError ? (ordersError as Error).message : null

  useEffect(() => {
    applyFilters()
  }, [orders, filters])

  // Função para invalidar cache e refetch
  const fetchOrders = () => {
    queryClient.invalidateQueries({ queryKey: ['maintenance-orders'] })
  }

  const applyFilters = () => {
    let filtered = [...orders]

    if (filters.equipment_id > 0) {
      filtered = filtered.filter(order => order.equipment_id === filters.equipment_id)
    }

    // Filtro por data inicial
    if (filters.start_date) {
      const startDate = new Date(filters.start_date)
      startDate.setHours(0, 0, 0, 0)
      filtered = filtered.filter(order => {
        if (!order.completion_date) return false
        const orderDate = new Date(order.completion_date)
        // Compara mantendo a data original do completion_date
        return orderDate >= startDate
      })
    }

    // Filtro por data final
    if (filters.end_date) {
      const endDate = new Date(filters.end_date)
      endDate.setHours(23, 59, 59, 999) // Fim do dia
      filtered = filtered.filter(order => {
        if (!order.completion_date) return false
        const orderDate = new Date(order.completion_date)
        // Compara mantendo a data original do completion_date
        return orderDate <= endDate
      })
    }

    setFilteredOrders(filtered)
  }

  const handleFilter = () => {
    applyFilters()
  }

  const handleExportExcel = () => {
    const dataToExport = filteredOrders.map(order => ({
      equipamento: getEquipmentName(order),
      empresa: order.service_provider || '-',
      dataManutencao: order.completion_date ? formatDateFullBR(order.completion_date) : '-',
      custo: order.cost ? formatCurrency(order.cost) : '-',
      garantiaAte: order.warranty_expiration ? formatDateFullBR(order.warranty_expiration) : 'Sem garantia',
      status: getStatusLabel(order.status),
      descricao: order.description || '-',
      termosGarantia: order.warranty_terms || '-',
      numeroNota: order.invoice_number || '-',
      observacoes: order.notes || '-'
    }))

    exportToExcel(
      dataToExport,
      [
        { header: 'Equipamento', key: 'equipamento', width: 20 },
        { header: 'Empresa', key: 'empresa', width: 20 },
        { header: 'Data da Manutenção', key: 'dataManutencao', width: 20 },
        { header: 'Custo', key: 'custo', width: 15 },
        { header: 'Garantia até', key: 'garantiaAte', width: 20 },
        { header: 'Status', key: 'status', width: 15 },
        { header: 'Descrição', key: 'descricao', width: 30 },
        { header: 'Termos da Garantia', key: 'termosGarantia', width: 30 },
        { header: 'Número da Nota', key: 'numeroNota', width: 15 },
        { header: 'Observações', key: 'observacoes', width: 30 }
      ],
      `Historico_Manutencoes_${new Date().toISOString().split('T')[0]}`
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.equipment_id || formData.equipment_id === 0) {
      alert('Por favor, selecione um equipamento')
      return
    }

    if (!formData.description) {
      alert('Por favor, preencha a descrição')
      return
    }

    try {
      // IMPORTANTE: Sempre enviar o campo documents, mesmo que seja null ou string vazia
      // Isso garante que o backend saiba que o campo foi enviado e pode processá-lo
      const documentsJson = documents.length > 0 ? JSON.stringify(documents) : null

      const dataToSend = {
        ...formData,
        title: formData.title || formData.description.substring(0, 100) || 'Manutenção', // Usar descrição como título se não fornecido
        equipment_id: formData.equipment_id,
        completion_date: formData.completion_date || null,
        warranty_expiration: formData.warranty_expiration || null,
        cost: formData.cost ? parseFloat(formData.cost.replace(',', '.')) : null,
        documents: documentsJson  // Sempre incluir, mesmo que seja null
      }

      // Debug: verificar o que está sendo enviado
      console.log('Enviando dados:', {
        ...dataToSend,
        documents: documents.length > 0 ? `${documents.length} documentos (${documentsJson?.length} chars)` : 'null (sem documentos)'
      })
      console.log('Documentos array:', documents)
      console.log('Documentos JSON:', documentsJson ? documentsJson.substring(0, 100) + '...' : 'null')

      if (editingOrder) {
        console.log(`Atualizando ordem ${editingOrder.id} com ${documents.length} documentos`)
        const response = await api.put(`/maintenance/orders/${editingOrder.id}`, dataToSend)
        console.log('Resposta da atualização:', response.data)
      } else {
        console.log(`Criando nova ordem com ${documents.length} documentos`)
        const response = await api.post('/maintenance/orders', dataToSend)
        console.log('Resposta da criação:', response.data)
      }
      fetchOrders()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeCreateView()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      console.error('Detalhes do erro:', err.response?.data)

      let errorMessage = 'Erro ao salvar ordem de manutenção'
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join('\n')
        } else {
          errorMessage = err.response.data.detail
        }
      }

      alert(errorMessage)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta ordem de manutenção?')) return
    try {
      await api.delete(`/maintenance/orders/${id}`)
      fetchOrders()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = async (order: MaintenanceOrder) => {
    // Garantir que a lista de equipamentos está carregada ao abrir a edição
    queryClient.invalidateQueries({ queryKey: ['maintenance-equipment'] })
    // Buscar a ordem completa (com documentos) antes de editar
    try {
      const response = await api.get(`/maintenance/orders/${order.id}`)
      const fullOrder = response.data

      setEditingOrder(fullOrder)

      const equipmentId = Number(fullOrder.equipment_id || order.equipment_id)
      console.log(`[DEBUG] Editando Ordem ${order.id}: equipment_id=${equipmentId}`)

      setFormData({
        equipment_id: equipmentId,
        title: fullOrder.title || order.title,
        description: fullOrder.description || order.description,
        status: fullOrder.status || order.status || 'PENDENTE',
        priority: fullOrder.priority || order.priority || 'MEDIA',
        service_provider: fullOrder.service_provider || order.service_provider || '',
        completion_date: toDateInputValue(fullOrder.completion_date || order.completion_date),
        cost: (fullOrder.cost || order.cost) ? (fullOrder.cost || order.cost).toString().replace('.', ',') : '',
        warranty_expiration: toDateInputValue(fullOrder.warranty_expiration || order.warranty_expiration),
        warranty_terms: fullOrder.warranty_terms || order.warranty_terms || '',
        invoice_number: fullOrder.invoice_number || order.invoice_number || '',
        notes: fullOrder.notes || order.notes || ''
      })

      // Carregar documentos da ordem completa
      if (fullOrder.documents) {
        try {
          const parsedDocs = JSON.parse(fullOrder.documents)
          setDocuments(Array.isArray(parsedDocs) ? parsedDocs : [])
        } catch (e) {
          console.error('Erro ao parsear documentos:', e)
          setDocuments([])
        }
      } else {
        setDocuments([])
      }

      setIsEditingInline(true)
    } catch (err) {
      console.error('Erro ao carregar detalhes da ordem:', err)
      alert('Erro ao carregar detalhes da ordem para edição')
    }
  }

  const cancelEdit = () => {
    setIsEditingInline(false)
    setEditingOrder(null)
    setFormData({
      equipment_id: equipment.length > 0 ? equipment[0].id : 0,
      title: '',
      description: '',
      status: 'PENDENTE',
      priority: 'MEDIA',
      service_provider: '',
      completion_date: '',
      cost: '',
      warranty_expiration: '',
      warranty_terms: '',
      invoice_number: '',
      notes: ''
    })
    setDocuments([])
  }

  const openCreateView = () => {
    setEditingOrder(null)
    setFormData({
      equipment_id: equipment.length > 0 ? equipment[0].id : 0,
      title: '',
      description: '',
      status: 'PENDENTE',
      priority: 'MEDIA',
      service_provider: '',
      completion_date: '',
      cost: '',
      warranty_expiration: '',
      warranty_terms: '',
      invoice_number: '',
      notes: ''
    })
    setDocuments([])
    setViewMode('create')
  }

  const closeCreateView = () => {
    setViewMode('list')
    setEditingOrder(null)
    setDocuments([])
  }

  const getStatusColor = (status: string) => {
    // Normalizar status para maiúsculas para garantir compatibilidade
    const normalizedStatus = status?.toUpperCase() || ''
    const colors: Record<string, string> = {
      'PENDENTE': 'bg-red-100 text-red-800',
      'EM_ANDAMENTO': 'bg-yellow-100 text-yellow-800',
      'CONCLUIDA': 'bg-green-100 text-green-800',
      'CANCELADA': 'bg-gray-100 text-gray-800'
    }
    return colors[normalizedStatus] || 'bg-gray-100 text-gray-800'
  }

  const getStatusLabel = (status: string) => {
    if (!status) return 'Desconhecido'

    // Normalizar status para maiúsculas e remover espaços
    const normalizedStatus = status.toUpperCase().trim()

    // Mapeamento direto (mais confiável e rápido)
    const statusMap: Record<string, string> = {
      'PENDENTE': 'Pendente',
      'EM_ANDAMENTO': 'Em Andamento',
      'CONCLUIDA': 'Concluída',
      'CANCELADA': 'Cancelada'
    }

    // Buscar no mapeamento primeiro (cobre todos os casos normalizados)
    const label = statusMap[normalizedStatus]
    if (label) {
      return label
    }

    // Se não encontrar, buscar no STATUS_OPTIONS como fallback
    const option = STATUS_OPTIONS.find(opt => opt.value === normalizedStatus || opt.value.toUpperCase() === normalizedStatus)
    if (option) {
      return option.label
    }

    // Último fallback: formatar o status manualmente
    // Converte "em_andamento" para "Em Andamento"
    return normalizedStatus
      .split('_')
      .map(word => word.charAt(0) + word.slice(1).toLowerCase())
      .join(' ')
  }

  const getEquipmentName = (order: MaintenanceOrder) => {
    if (order.equipment_name) return order.equipment_name
    const id = Number(order.equipment_id)
    const eq = equipment.find(e => Number(e.id) === id)
    return eq ? eq.name : 'Desconhecido'
  }

  const formatCurrency = (value: number | null) => {
    if (!value) return 'R$ -'
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  if (loading) {
    return <Loading message="Carregando ordens de manutenção..." />
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Erro: {error}</p>
        <button
          onClick={fetchOrders}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  return (
    <div>
      {viewMode === 'create' ? (
        // Tela completa de cadastro
        <div className="min-h-screen bg-gray-50">
          <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={closeCreateView}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Voltar"
                >
                  <ArrowLeft className="h-5 w-5 text-gray-600" />
                </button>
                <h1 className="text-2xl font-bold text-gray-900">Nova Ordem de Manutenção</h1>
              </div>
            </div>
          </div>

          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                {/* Coluna Esquerda */}
                <div className="space-y-4 md:space-y-6">
                  {/* Equipamento */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Equipamento *</label>
                    <select
                      value={String(formData.equipment_id)}
                      onChange={(e) => setFormData({ ...formData, equipment_id: parseInt(e.target.value, 10) || 0 })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                      disabled={equipmentLoading}
                    >
                      <option value="0">
                        {equipmentLoading ? 'Carregando equipamentos...' : equipmentError ? 'Erro ao carregar. Tente novamente.' : 'Selecione o equipamento...'}
                      </option>
                      {equipmentOptions.map(eq => (
                        <option key={eq.id} value={String(eq.id)}>{eq.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Título */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Título *</label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Ex: Troca de óleo"
                      required
                    />
                  </div>

                  {/* Prioridade */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Prioridade *</label>
                    <select
                      value={formData.priority}
                      onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                    >
                      <option value="BAIXA">Baixa</option>
                      <option value="MEDIA">Média</option>
                      <option value="ALTA">Alta</option>
                      <option value="URGENTE">Urgente</option>
                    </select>
                  </div>

                  {/* Status */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status *</label>
                    <select
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                    >
                      {STATUS_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Empresa Prestadora do Serviço */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Empresa Prestadora do Serviço</label>
                    <input
                      type="text"
                      value={formData.service_provider}
                      onChange={(e) => setFormData({ ...formData, service_provider: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Ex: Junior Moto Peças"
                    />
                  </div>

                  {/* Data da Manutenção */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Data da Manutenção</label>
                    <DateInput
                      value={formData.completion_date}
                      onChange={(value) => setFormData({ ...formData, completion_date: value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  {/* Custo */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Custo</label>
                    <input
                      type="text"
                      value={formData.cost}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^\d,]/g, '')
                        setFormData({ ...formData, cost: value })
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="0,00"
                    />
                  </div>

                  {/* Data de Vencimento da Garantia */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Data de Vencimento da Garantia</label>
                    <DateInput
                      value={formData.warranty_expiration}
                      onChange={(value) => setFormData({ ...formData, warranty_expiration: value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                {/* Coluna Direita */}
                <div className="space-y-4 md:space-y-6">
                  {/* Descrição */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      rows={5}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Descreva a manutenção realizada..."
                      required
                    />
                  </div>

                  {/* Termos da Garantia */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Termos da Garantia</label>
                    <textarea
                      value={formData.warranty_terms}
                      onChange={(e) => setFormData({ ...formData, warranty_terms: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Termos e condições da garantia..."
                    />
                  </div>

                  {/* Número da Nota Fiscal */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Número da Nota Fiscal</label>
                    <input
                      type="text"
                      value={formData.invoice_number}
                      onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Número da nota fiscal"
                    />
                  </div>

                  {/* Observações */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                    <textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Observações adicionais..."
                    />
                  </div>

                  {/* Upload de Documentos */}
                  <div>
                    <DocumentUpload
                      documents={documents}
                      onChange={setDocuments}
                      maxFiles={10}
                      maxSizeMB={10}
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={closeCreateView}
                  className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 flex items-center justify-center"
                >
                  <Save className="mr-2 h-5 w-5" />
                  Criar Ordem
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : !isEditingInline ? (
        // Tela de lista
        <>
          {/* Cabeçalho */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Clock className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              Histórico de Manutenções
            </h1>
            <div className="flex gap-2 w-full sm:w-auto">
              <button
                onClick={handleExportExcel}
                className="flex-1 sm:flex-none px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors flex items-center justify-center"
              >
                <FileSpreadsheet className="mr-2 h-5 w-5" />
                Exportar Excel
              </button>
              <button
                onClick={() => openCreateView()}
                className="flex-1 sm:flex-none px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <Plus className="mr-2 h-5 w-5" />
                Nova Manutenção
              </button>
            </div>
          </div>

          {/* Filtros */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Equipamento</label>
                <select
                  value={String(filters.equipment_id)}
                  onChange={(e) => setFilters({ ...filters, equipment_id: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="0">Todos os Equipamentos</option>
                  {filterEquipmentOptions.map(eq => (
                    <option key={eq.id} value={String(eq.id)}>{eq.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
                <DateInput
                  value={filters.start_date}
                  onChange={(value) => setFilters({ ...filters, start_date: value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
                <DateInput
                  value={filters.end_date}
                  onChange={(value) => setFilters({ ...filters, end_date: value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleFilter}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
                >
                  <Filter className="mr-2 h-5 w-5" />
                  Filtrar
                </button>
              </div>
            </div>
          </div>

          {/* Lista de Ordens */}
          {filteredOrders.length === 0 ? (
            <div className="bg-white shadow rounded-lg p-6">
              <p className="text-gray-600 text-center py-8">
                Nenhuma ordem de manutenção encontrada.
              </p>
            </div>
          ) : (
            <>
              {/* Visualização em Cards para Mobile/Tablet */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
                {filteredOrders.map((order) => (
                  <div key={order.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                    {/* Cabeçalho do Card */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold text-gray-900">{getEquipmentName(order)}</h3>
                          {(order.documents || order.has_documents) && (
                            <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                          )}
                        </div>
                        {order.service_provider && (
                          <div className="text-sm text-gray-500 mt-1">
                            {order.service_provider}
                          </div>
                        )}
                      </div>
                      <div>
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(order.status)}`}>
                          {getStatusLabel(order.status || '')}
                        </span>
                      </div>
                    </div>

                    {/* Informações do Card */}
                    <div className="space-y-2 text-sm">
                      {order.completion_date && (
                        <div>
                          <span className="font-medium text-gray-700">Data da Manutenção:</span>
                          <span className="ml-2 text-gray-900">{formatDateFullBR(order.completion_date)}</span>
                        </div>
                      )}
                      {order.cost && (
                        <div>
                          <span className="font-medium text-gray-700">Custo:</span>
                          <span className="ml-2 text-gray-900">{formatCurrency(order.cost)}</span>
                        </div>
                      )}
                      <div>
                        <span className="font-medium text-gray-700">Garantia até:</span>
                        <span className="ml-2 text-gray-900">
                          {order.warranty_expiration ? formatDateFullBR(order.warranty_expiration) : 'Sem garantia'}
                        </span>
                      </div>
                      {order.description && (
                        <div>
                          <span className="font-medium text-gray-700">Descrição:</span>
                          <span className="ml-2 text-gray-900 line-clamp-2">{order.description}</span>
                        </div>
                      )}
                    </div>

                    {/* Ações do Card */}
                    <div className="flex gap-2 pt-3 border-t border-gray-200">
                      <button
                        onClick={() => startEdit(order)}
                        className="flex-1 flex items-center justify-center px-3 py-2 bg-yellow-100 text-yellow-600 text-sm rounded-md hover:bg-yellow-200"
                      >
                        <Edit2 className="h-4 w-4 mr-1" />
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(order.id)}
                        className="flex items-center justify-center px-3 py-2 border border-red-600 text-red-600 text-sm rounded-md hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Excluir
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Visualização em Tabela para Desktop */}
              <div className="hidden lg:block bg-white shadow rounded-lg overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Equipamento
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Empresa
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data da Manutenção
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Custo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Garantia até
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredOrders.map((order) => (
                      <tr key={order.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <div className="text-sm font-medium text-gray-900">{getEquipmentName(order)}</div>
                            {order.documents && (
                              <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{order.service_provider || '-'}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {order.completion_date ? formatDateFullBR(order.completion_date) : '-'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{formatCurrency(order.cost)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {order.warranty_expiration ? formatDateFullBR(order.warranty_expiration) : 'Sem garantia'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(order.status)}`}>
                            {getStatusLabel(order.status || '')}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => startEdit(order)}
                              className="p-2 bg-yellow-100 text-yellow-600 rounded hover:bg-yellow-200"
                              title="Editar"
                            >
                              <Edit2 className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(order.id)}
                              className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
                              title="Excluir"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      ) : (
        /* Formulário de Edição na Tela */
        <div className="bg-white shadow rounded-lg p-4 md:p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl md:text-2xl font-bold text-gray-900 flex items-center">
              <ArrowLeft
                onClick={cancelEdit}
                className="mr-3 h-6 w-6 cursor-pointer text-gray-600 hover:text-gray-900"
              />
              Editar Manutenção
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
              {/* Coluna Esquerda */}
              <div className="space-y-4 md:space-y-6">
                {/* Equipamento */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Equipamento *</label>
                  <select
                    value={String(formData.equipment_id)}
                    onChange={(e) => setFormData({ ...formData, equipment_id: parseInt(e.target.value, 10) || 0 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                    disabled={equipmentLoading}
                  >
                    <option value="0">
                      {equipmentLoading ? 'Carregando equipamentos...' : equipmentError ? 'Erro ao carregar. Tente novamente.' : 'Selecione o equipamento...'}
                    </option>
                    {equipmentOptions.map(eq => (
                      <option key={eq.id} value={String(eq.id)}>{eq.name}</option>
                    ))}
                  </select>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status *</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  >
                    {STATUS_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>

                {/* Empresa Prestadora do Serviço */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Empresa Prestadora do Serviço</label>
                  <input
                    type="text"
                    value={formData.service_provider}
                    onChange={(e) => setFormData({ ...formData, service_provider: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Ex: Junior Moto Peças"
                  />
                </div>

                {/* Data da Manutenção */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data da Manutenção</label>
                  <DateInput
                    value={formData.completion_date}
                    onChange={(value) => setFormData({ ...formData, completion_date: value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                {/* Custo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Custo</label>
                  <input
                    type="text"
                    value={formData.cost}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^\d,]/g, '')
                      setFormData({ ...formData, cost: value })
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="0,00"
                  />
                </div>

                {/* Data de Vencimento da Garantia */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data de Vencimento da Garantia</label>
                  <DateInput
                    value={formData.warranty_expiration}
                    onChange={(value) => setFormData({ ...formData, warranty_expiration: value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                {/* Upload de Documentos */}
                <div>
                  <DocumentUpload
                    documents={documents}
                    onChange={setDocuments}
                    maxFiles={10}
                    maxSizeMB={10}
                  />
                </div>
              </div>

              {/* Coluna Direita */}
              <div className="space-y-4 md:space-y-6">
                {/* Descrição */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Descreva a manutenção realizada..."
                    required
                  />
                </div>

                {/* Termos da Garantia */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Termos da Garantia</label>
                  <textarea
                    value={formData.warranty_terms}
                    onChange={(e) => setFormData({ ...formData, warranty_terms: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Termos e condições da garantia..."
                  />
                </div>

                {/* Número da Nota Fiscal */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Número da Nota Fiscal</label>
                  <input
                    type="text"
                    value={formData.invoice_number}
                    onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Número da nota fiscal"
                  />
                </div>

                {/* Observações */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Observações adicionais..."
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={cancelEdit}
                className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="w-full sm:w-auto px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
