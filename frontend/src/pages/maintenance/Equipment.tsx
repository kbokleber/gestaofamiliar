import { useState, useEffect } from 'react'
import { Settings, Plus, Edit2, Trash2, Save, Paperclip, ArrowLeft, Filter } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
import Loading from '../../components/Loading'
import { formatDateBR, toDateInputValue } from '../../utils/dateUtils'

interface Equipment {
  id: number
  name: string
  type: string | null
  brand: string | null
  model: string | null
  serial_number: string | null
  purchase_date: string | null
  warranty_expiry: string | null
  status: string
  notes: string
  documents: string | null
  created_at: string
  updated_at: string
}

const STATUS_OPTIONS = [
  { value: 'OPERACIONAL', label: 'Operacional' },
  { value: 'EM_MANUTENCAO', label: 'Em Manutenção' },
  { value: 'FORA_DE_USO', label: 'Fora de Uso' },
  { value: 'RESERVA', label: 'Reserva' }
]

const TYPE_OPTIONS = [
  { value: 'eletronico', label: 'Eletrônico' },
  { value: 'eletrodomestico', label: 'Eletrodoméstico' },
  { value: 'movel', label: 'Móvel' },
  { value: 'veiculo', label: 'Veículo' },
  { value: 'outro', label: 'Outro' }
]

const EMPTY_EQUIPMENT: Equipment[] = []

export default function Equipment() {
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<'list' | 'create'>('list')
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(null)
  const [filteredEquipment, setFilteredEquipment] = useState<Equipment[]>([])
  const [filters, setFilters] = useState({
    type: '',
    status: '',
    search: ''
  })
  const [formData, setFormData] = useState({
    name: '',
    type: '',
    brand: '',
    model: '',
    serial_number: '',
    purchase_date: '',
    warranty_expiry: '',
    status: 'OPERACIONAL',
    notes: ''
  })
  const [documents, setDocuments] = useState<Document[]>([])

  // Carregar dados do localStorage como placeholder
  const getPlaceholderEquipment = (): Equipment[] | undefined => {
    try {
      const cached = localStorage.getItem('equipment-list-cache')
      return cached ? JSON.parse(cached) : undefined
    } catch {
      return undefined
    }
  }

  // React Query com default estável para evitar loop de re-render
  const { data: equipment = EMPTY_EQUIPMENT, isLoading: loading, error: equipmentError } = useQuery<Equipment[]>({
    queryKey: ['maintenance-equipment'],
    queryFn: async () => {
      const response = await api.get('/maintenance/equipment', { params: { include_documents: false } })
      try {
        const cacheData = response.data.map((e: Equipment) => ({
          id: e.id, name: e.name, type: e.type, status: e.status
        }))
        localStorage.setItem('equipment-list-cache', JSON.stringify(cacheData))
      } catch { /* localStorage cheio, ignorar */ }
      return response.data
    },
    placeholderData: getPlaceholderEquipment(),
    staleTime: 5 * 60 * 1000,
  })

  const error = equipmentError ? (equipmentError as Error).message : null

  const applyFilters = () => {
    let filtered = [...equipment]
    if (filters.type) {
      filtered = filtered.filter(e => e.type === filters.type)
    }
    if (filters.status) {
      filtered = filtered.filter(e => e.status === filters.status)
    }
    if (filters.search.trim()) {
      const term = filters.search.trim().toLowerCase()
      filtered = filtered.filter(e =>
        (e.name && e.name.toLowerCase().includes(term)) ||
        (e.brand && e.brand.toLowerCase().includes(term)) ||
        (e.model && e.model.toLowerCase().includes(term)) ||
        (e.serial_number && e.serial_number.toLowerCase().includes(term))
      )
    }
    setFilteredEquipment(filtered)
  }

  useEffect(() => {
    let filtered = [...equipment]
    if (filters.type) {
      filtered = filtered.filter(e => e.type === filters.type)
    }
    if (filters.status) {
      filtered = filtered.filter(e => e.status === filters.status)
    }
    if (filters.search.trim()) {
      const term = filters.search.trim().toLowerCase()
      filtered = filtered.filter(e =>
        (e.name && e.name.toLowerCase().includes(term)) ||
        (e.brand && e.brand.toLowerCase().includes(term)) ||
        (e.model && e.model.toLowerCase().includes(term)) ||
        (e.serial_number && e.serial_number.toLowerCase().includes(term))
      )
    }
    setFilteredEquipment(filtered)
  }, [equipment, filters.type, filters.status, filters.search])

  // Função para invalidar cache e refetch
  const fetchEquipment = () => {
    queryClient.invalidateQueries({ queryKey: ['maintenance-equipment'] })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name) {
      alert('Por favor, preencha o nome do equipamento')
      return
    }
    
    try {
      const dataToSend = {
        ...formData,
        purchase_date: formData.purchase_date || null,
        warranty_expiry: formData.warranty_expiry || null,
        type: formData.type || null,
        brand: formData.brand || null,
        model: formData.model || null,
        serial_number: formData.serial_number || null,
        service_provider: '', // Campo obrigatório no schema
        notes: formData.notes || '',
        documents: documents.length > 0 ? JSON.stringify(documents) : null
      }
      
      if (editingEquipment) {
        await api.put(`/maintenance/equipment/${editingEquipment.id}`, dataToSend)
      } else {
        await api.post('/maintenance/equipment', dataToSend)
      }
      fetchEquipment()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeCreateView()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      console.error('Detalhes do erro:', err.response?.data)
      
      let errorMessage = 'Erro ao salvar equipamento'
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
    if (!confirm('Deseja realmente excluir este equipamento?')) return
    try {
      await api.delete(`/maintenance/equipment/${id}`)
      fetchEquipment()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = (equipmentItem: Equipment) => {
    setEditingEquipment(equipmentItem)
    setFormData({
      name: equipmentItem.name,
      type: equipmentItem.type || '',
      brand: equipmentItem.brand || '',
      model: equipmentItem.model || '',
      serial_number: equipmentItem.serial_number || '',
      purchase_date: toDateInputValue(equipmentItem.purchase_date),
      warranty_expiry: toDateInputValue(equipmentItem.warranty_expiry),
      status: equipmentItem.status || 'OPERACIONAL',
      notes: equipmentItem.notes || ''
    })
    // Carregar documentos
    if (equipmentItem.documents) {
      try {
        setDocuments(JSON.parse(equipmentItem.documents))
      } catch (e) {
        setDocuments([])
      }
    } else {
      setDocuments([])
    }
    setIsEditingInline(true)
  }

  const cancelEdit = () => {
    setIsEditingInline(false)
    setEditingEquipment(null)
    setFormData({
      name: '',
      type: '',
      brand: '',
      model: '',
      serial_number: '',
      purchase_date: '',
      warranty_expiry: '',
      status: 'OPERACIONAL',
      notes: ''
    })
    setDocuments([])
  }

  const openCreateView = () => {
    setEditingEquipment(null)
    setFormData({
      name: '',
      type: '',
      brand: '',
      model: '',
      serial_number: '',
      purchase_date: '',
      warranty_expiry: '',
      status: 'OPERACIONAL',
      notes: ''
    })
    setDocuments([])
    setViewMode('create')
  }

  const closeCreateView = () => {
    setViewMode('list')
    setEditingEquipment(null)
    setDocuments([])
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'OPERACIONAL': 'bg-green-100 text-green-800',
      'EM_MANUTENCAO': 'bg-yellow-100 text-yellow-800',
      'FORA_DE_USO': 'bg-red-100 text-red-800',
      'RESERVA': 'bg-blue-100 text-blue-800'
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const getStatusLabel = (status: string) => {
    const option = STATUS_OPTIONS.find(opt => opt.value === status)
    return option ? option.label : status
  }

  const getTypeLabel = (type: string | null) => {
    if (!type) return '-'
    const option = TYPE_OPTIONS.find(opt => opt.value === type)
    return option ? option.label : type
  }

  if (loading) {
    return <Loading message="Carregando equipamentos..." />
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Erro: {error}</p>
        <button 
          onClick={fetchEquipment}
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
                <h1 className="text-2xl font-bold text-gray-900">Novo Equipamento</h1>
              </div>
            </div>
          </div>
          
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
              {/* Nome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Equipamento *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Ex: Notebook Dell, Geladeira Brastemp"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Tipo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({...formData, type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  >
                    <option value="">Selecione...</option>
                    {TYPE_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({...formData, status: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  >
                    {STATUS_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Marca */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({...formData, brand: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                    placeholder="Ex: Dell, Samsung, Brastemp"
                  />
                </div>

                {/* Modelo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({...formData, model: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                    placeholder="Ex: Inspiron 15, RT46"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Número de Série */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Número de Série</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({...formData, serial_number: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                    placeholder="Número de série do equipamento"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Data de Compra */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data de Compra</label>
                  <DateInput
                    value={formData.purchase_date}
                    onChange={(value) => setFormData({...formData, purchase_date: value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>

                {/* Data de Vencimento da Garantia */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Vencimento da Garantia</label>
                  <DateInput
                    value={formData.warranty_expiry}
                    onChange={(value) => setFormData({...formData, warranty_expiry: value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>
              </div>

              {/* Observações */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Informações adicionais sobre o equipamento..."
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
                  className="w-full sm:w-auto px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 flex items-center justify-center"
                >
                  <Save className="mr-2 h-5 w-5" />
                  Criar Equipamento
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : !isEditingInline ? (
        // Tela de lista
        <>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Settings className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              Equipamentos
            </h1>
            <button 
              onClick={() => openCreateView()}
              className="w-full sm:w-auto px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-center"
            >
              <Plus className="mr-2 h-5 w-5" />
              Novo Equipamento
            </button>
          </div>

          {/* Filtros */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Busca</label>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Nome, marca, modelo ou série..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select
                  value={filters.type}
                  onChange={(e) => setFilters({ ...filters, type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="">Todos os tipos</option>
                  {TYPE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="">Todos os status</option>
                  {STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={applyFilters}
                  className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-center"
                >
                  <Filter className="mr-2 h-5 w-5" />
                  Filtrar
                </button>
              </div>
            </div>
          </div>

          {filteredEquipment.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600 text-center py-8">
            {equipment.length === 0
              ? 'Nenhum equipamento cadastrado. Clique em "Novo Equipamento" para adicionar.'
              : 'Nenhum equipamento encontrado com os filtros aplicados.'}
          </p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
            {filteredEquipment.map((item) => (
              <div key={item.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                {/* Cabeçalho do Card */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
                      {item.documents && (
                        <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                      )}
                    </div>
                    {item.serial_number && (
                      <div className="text-sm text-gray-500 mt-1">
                        SN: {item.serial_number}
                      </div>
                    )}
                  </div>
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(item.status)}`}>
                    {getStatusLabel(item.status)}
                  </span>
                </div>

                {/* Informações do Card */}
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Tipo:</span>
                    <span className="ml-2 text-gray-900">{getTypeLabel(item.type)}</span>
                  </div>
                  {(item.brand || item.model) && (
                    <div>
                      <span className="font-medium text-gray-700">Marca/Modelo:</span>
                      <span className="ml-2 text-gray-900">
                        {item.brand || ''} {item.model ? `- ${item.model}` : ''}
                      </span>
                    </div>
                  )}
                  {item.purchase_date && (
                    <div>
                      <span className="font-medium text-gray-700">Data de Compra:</span>
                      <span className="ml-2 text-gray-900">{formatDateBR(item.purchase_date)}</span>
                    </div>
                  )}
                </div>

                {/* Ações do Card */}
                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button 
                    onClick={() => startEdit(item)}
                    className="flex-1 flex items-center justify-center px-3 py-2 bg-orange-600 text-white text-sm rounded-md hover:bg-orange-700"
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Editar
                  </button>
                  <button 
                    onClick={() => handleDelete(item.id)}
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
                    Tipo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Marca/Modelo
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
                {filteredEquipment.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{item.name}</div>
                          {item.serial_number && (
                            <div className="text-xs text-gray-500">SN: {item.serial_number}</div>
                          )}
                        </div>
                        {item.documents && (
                          <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{getTypeLabel(item.type)}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600">
                        {item.brand || ''} {item.model ? `- ${item.model}` : ''}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(item.status)}`}>
                        {getStatusLabel(item.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button 
                        onClick={() => startEdit(item)}
                        className="text-orange-600 hover:text-orange-900 mr-3"
                        title="Editar"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => handleDelete(item.id)}
                        className="text-red-600 hover:text-red-900"
                        title="Excluir"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
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
              Editar Equipamento
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            {/* Nome */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Equipamento *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="Ex: Notebook Dell, Geladeira Brastemp"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Tipo */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({...formData, type: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="">Selecione...</option>
                  {TYPE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({...formData, status: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                  {STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Marca */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
                <input
                  type="text"
                  value={formData.brand}
                  onChange={(e) => setFormData({...formData, brand: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Ex: Dell, Samsung, Brastemp"
                />
              </div>

              {/* Modelo */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({...formData, model: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Ex: Inspiron 15, RT46"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Número de Série */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Número de Série</label>
                <input
                  type="text"
                  value={formData.serial_number}
                  onChange={(e) => setFormData({...formData, serial_number: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="Número de série do equipamento"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Data de Compra */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Compra</label>
                <DateInput
                  value={formData.purchase_date}
                  onChange={(value) => setFormData({...formData, purchase_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              {/* Data de Vencimento da Garantia */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vencimento da Garantia</label>
                <DateInput
                  value={formData.warranty_expiry}
                  onChange={(value) => setFormData({...formData, warranty_expiry: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="Informações adicionais sobre o equipamento..."
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
                className="w-full sm:w-auto px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 flex items-center justify-center"
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
