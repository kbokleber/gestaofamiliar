import { useState, useEffect } from 'react'
import { Settings, Plus, Edit2, Trash2, X, Save, Paperclip, ArrowLeft } from 'lucide-react'
import api from '../../lib/api'
import Modal from '../../components/Modal'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
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

export default function Equipment() {
  const [equipment, setEquipment] = useState<Equipment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(null)
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

  useEffect(() => {
    fetchEquipment()
  }, [])

  const fetchEquipment = async () => {
    try {
      setLoading(true)
      const response = await api.get('/maintenance/equipment')
      setEquipment(response.data)
      setError(null)
    } catch (err: any) {
      console.error('Erro ao buscar equipamentos:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar equipamentos')
    } finally {
      setLoading(false)
    }
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
        closeModal()
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

  const openModal = () => {
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
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
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
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-600">Carregando...</p>
      </div>
    )
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
      {!isEditingInline ? (
        <>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Settings className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              Equipamentos
            </h1>
            <button 
              onClick={() => openModal()}
              className="w-full sm:w-auto px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-center"
            >
              <Plus className="mr-2 h-5 w-5" />
              Novo Equipamento
            </button>
          </div>

          {equipment.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600 text-center py-8">
            Nenhum equipamento cadastrado. Clique em "Novo Equipamento" para adicionar.
          </p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
            {equipment.map((item) => (
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
                {equipment.map((item) => (
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

      {/* Modal de Criar */}
      <Modal isOpen={isModalOpen} onClose={closeModal} title="Novo Equipamento">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          <div className="sticky top-0 bg-white border-b border-gray-200 px-4 md:px-6 py-4 flex items-center justify-between z-10">
            <h3 className="text-lg md:text-xl font-semibold text-gray-900">
              Novo Equipamento
            </h3>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5 md:h-6 md:w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-4 md:p-6 space-y-4 md:space-y-6 overflow-y-auto flex-1">
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

            <div className="sticky bottom-0 bg-white border-t border-gray-200 pt-4 pb-2 flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 mt-6">
              <button
                type="button"
                onClick={closeModal}
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
      </Modal>
    </div>
  )
}
