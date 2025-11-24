import { useState, useEffect } from 'react'
import { Calendar, Plus, Edit2, Trash2, X, Save, User, Paperclip, ArrowLeft, Filter, FileSpreadsheet } from 'lucide-react'
import api from '../../lib/api'
import Modal from '../../components/Modal'
import DateTimeInput from '../../components/DateTimeInput'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
import { formatDateTimeBR, toDateTimeInputValue } from '../../utils/dateUtils'
import { exportToExcel } from '../../utils/excelUtils'

interface FamilyMember {
  id: number
  name: string
}

interface Appointment {
  id: number
  family_member_id: number
  doctor_name: string
  specialty: string
  appointment_date: string
  location: string
  reason: string
  diagnosis: string
  prescription: string
  next_appointment: string | null
  notes: string
  documents: string | null
  created_at: string
  updated_at: string
  family_member?: FamilyMember
}

export default function Appointments() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [filteredAppointments, setFilteredAppointments] = useState<Appointment[]>([])
  const [showUpcomingOnly, setShowUpcomingOnly] = useState(true)
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    member_id: 0,
    start_date: '',
    end_date: ''
  })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null)
  const [formData, setFormData] = useState({
    family_member_id: 0,
    doctor_name: '',
    specialty: '',
    appointment_date: '',
    location: '',
    reason: '',
    diagnosis: '',
    prescription: '',
    next_appointment: '',
    notes: ''
  })
  const [documents, setDocuments] = useState<Document[]>([])

  useEffect(() => {
    fetchAppointments()
    fetchMembers()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [appointments, showUpcomingOnly, filters])

  const applyFilters = () => {
    let filtered = [...appointments]

    // Filtro por membro
    if (filters.member_id > 0) {
      filtered = filtered.filter(appointment => appointment.family_member_id === filters.member_id)
    }

    // Filtro por data inicial (considera data/hora completa)
    if (filters.start_date) {
      const startDate = new Date(filters.start_date)
      startDate.setHours(0, 0, 0, 0)
      filtered = filtered.filter(appointment => {
        const appointmentDate = new Date(appointment.appointment_date)
        // Compara mantendo a hora original do appointment_date
        return appointmentDate >= startDate
      })
    }

    // Filtro por data final (considera data/hora completa)
    if (filters.end_date) {
      const endDate = new Date(filters.end_date)
      endDate.setHours(23, 59, 59, 999)
      filtered = filtered.filter(appointment => {
        const appointmentDate = new Date(appointment.appointment_date)
        // Compara mantendo a hora original do appointment_date
        return appointmentDate <= endDate
      })
    }

    // Filtro por próximas consultas
    if (showUpcomingOnly) {
      const now = new Date()
      filtered = filtered.filter(appointment => {
        const appointmentDate = new Date(appointment.appointment_date)
        return appointmentDate > now
      })
    }

    setFilteredAppointments(filtered)
  }

  const handleFilter = () => {
    applyFilters()
  }

  const handleExportExcel = () => {
    const dataToExport = filteredAppointments.map(appointment => ({
      paciente: getMemberName(appointment.family_member_id),
      dataHora: formatDateTimeBR(appointment.appointment_date),
      medico: appointment.doctor_name || '-',
      especialidade: appointment.specialty || '-',
      local: appointment.location || '-',
      motivo: appointment.reason || '-',
      diagnostico: appointment.diagnosis || '-',
      proximaConsulta: appointment.next_appointment ? formatDateTimeBR(appointment.next_appointment) : '-',
      observacoes: appointment.notes || '-'
    }))

    exportToExcel(
      dataToExport,
      [
        { header: 'Paciente', key: 'paciente', width: 20 },
        { header: 'Data/Hora', key: 'dataHora', width: 20 },
        { header: 'Médico', key: 'medico', width: 20 },
        { header: 'Especialidade', key: 'especialidade', width: 20 },
        { header: 'Local', key: 'local', width: 20 },
        { header: 'Motivo', key: 'motivo', width: 30 },
        { header: 'Diagnóstico', key: 'diagnostico', width: 30 },
        { header: 'Próxima Consulta', key: 'proximaConsulta', width: 20 },
        { header: 'Observações', key: 'observacoes', width: 30 }
      ],
      `Consultas_Medicas_${new Date().toISOString().split('T')[0]}`
    )
  }

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      const response = await api.get('/healthcare/appointments')
      setAppointments(response.data)
      setError(null)
    } catch (err: any) {
      console.error('Erro ao buscar consultas:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar consultas')
    } finally {
      setLoading(false)
    }
  }

  const fetchMembers = async () => {
    try {
      const response = await api.get('/healthcare/members')
      setMembers(response.data)
    } catch (err: any) {
      console.error('Erro ao buscar membros:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validar campos obrigatórios
    if (!formData.family_member_id || formData.family_member_id === 0) {
      alert('Por favor, selecione um paciente')
      return
    }
    
    if (!formData.appointment_date) {
      alert('Por favor, preencha a data e hora da consulta')
      return
    }
    
    try {
      // Preparar dados para envio
      const dataToSend = {
        ...formData,
        // Se next_appointment estiver vazio, enviar null
        next_appointment: formData.next_appointment || null,
        // Serializar documentos como JSON
        documents: documents.length > 0 ? JSON.stringify(documents) : null
      }
      
      if (editingAppointment) {
        await api.put(`/healthcare/appointments/${editingAppointment.id}`, dataToSend)
      } else {
        await api.post('/healthcare/appointments', dataToSend)
      }
      fetchAppointments()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeModal()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      console.error('Detalhes do erro:', err.response?.data)
      
      // Extrair mensagem de erro mais específica
      let errorMessage = 'Erro ao salvar consulta'
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
    if (!confirm('Deseja realmente excluir esta consulta?')) return
    try {
      await api.delete(`/healthcare/appointments/${id}`)
      fetchAppointments()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = (appointment: Appointment) => {
    setEditingAppointment(appointment)
    setFormData({
      family_member_id: appointment.family_member_id,
      doctor_name: appointment.doctor_name,
      specialty: appointment.specialty,
      appointment_date: toDateTimeInputValue(appointment.appointment_date),
      location: appointment.location || '',
      reason: appointment.reason,
      diagnosis: appointment.diagnosis || '',
      prescription: appointment.prescription || '',
      next_appointment: toDateTimeInputValue(appointment.next_appointment),
      notes: appointment.notes || ''
    })
    // Carregar documentos
    if (appointment.documents) {
      try {
        setDocuments(JSON.parse(appointment.documents))
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
    setEditingAppointment(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      doctor_name: '',
      specialty: '',
      appointment_date: '',
      location: '',
      reason: '',
      diagnosis: '',
      prescription: '',
      next_appointment: '',
      notes: ''
    })
    setDocuments([])
  }

  const openModal = () => {
    setEditingAppointment(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      doctor_name: '',
      specialty: '',
      appointment_date: '',
      location: '',
      reason: '',
      diagnosis: '',
      prescription: '',
      next_appointment: '',
      notes: ''
    })
    setDocuments([])
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingAppointment(null)
    setDocuments([])
  }


  const getMemberName = (memberId: number) => {
    const member = members.find(m => m.id === memberId)
    return member ? member.name : 'Desconhecido'
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
          onClick={fetchAppointments}
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
          {/* Cabeçalho */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Calendar className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              Consultas Médicas
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
                onClick={() => openModal()}
                className="flex-1 sm:flex-none px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <Plus className="mr-2 h-5 w-5" />
                Nova Consulta
              </button>
            </div>
          </div>

          {/* Filtros */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Paciente</label>
                <select
                  value={filters.member_id}
                  onChange={(e) => setFilters({...filters, member_id: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value={0}>Todos os Pacientes</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>{member.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
                <DateInput
                  value={filters.start_date}
                  onChange={(value) => setFilters({...filters, start_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
                <DateInput
                  value={filters.end_date}
                  onChange={(value) => setFilters({...filters, end_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={showUpcomingOnly}
                    onChange={(e) => setShowUpcomingOnly(e.target.checked)}
                    className="mr-2 rounded"
                  />
                  <span className="text-sm text-gray-700">Apenas próximas</span>
                </label>
                <button
                  onClick={handleFilter}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
                >
                  <Filter className="mr-2 h-5 w-5" />
                  Filtrar
                </button>
              </div>
            </div>
          </div>

          {filteredAppointments.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600 text-center py-8">
            Nenhuma consulta encontrada com os filtros aplicados.
          </p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
            {filteredAppointments.map((appointment) => (
              <div key={appointment.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                {/* Cabeçalho do Card */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{getMemberName(appointment.family_member_id)}</h3>
                      {appointment.documents && (
                        <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                      )}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {formatDateTimeBR(appointment.appointment_date)}
                    </div>
                  </div>
                </div>

                {/* Informações do Card */}
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Médico:</span>
                    <span className="ml-2 text-gray-900">{appointment.doctor_name}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Especialidade:</span>
                    <span className="ml-2 text-gray-900">{appointment.specialty}</span>
                  </div>
                  {appointment.location && (
                    <div>
                      <span className="font-medium text-gray-700">Local:</span>
                      <span className="ml-2 text-gray-900">{appointment.location}</span>
                    </div>
                  )}
                  {appointment.reason && (
                    <div>
                      <span className="font-medium text-gray-700">Motivo:</span>
                      <p className="mt-1 text-gray-900 text-xs line-clamp-2">{appointment.reason}</p>
                    </div>
                  )}
                </div>

                {/* Ações do Card */}
                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button 
                    onClick={() => startEdit(appointment)}
                    className="flex-1 flex items-center justify-center px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Editar
                  </button>
                  <button 
                    onClick={() => handleDelete(appointment.id)}
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
                  Paciente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data/Hora
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Médico
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Especialidade
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Local
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAppointments.map((appointment) => (
                <tr key={appointment.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <User className="h-5 w-5 text-gray-400 mr-2" />
                      <div className="text-sm font-medium text-gray-900">
                        {getMemberName(appointment.family_member_id)}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {formatDateTimeBR(appointment.appointment_date)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{appointment.doctor_name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600">{appointment.specialty}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600">{appointment.location || '-'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => startEdit(appointment)}
                      className="text-green-600 hover:text-green-900 mr-3"
                      title="Editar"
                    >
                      <Edit2 className="h-5 w-5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(appointment.id)}
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
              Editar Consulta
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            {/* Paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
              <select
                value={formData.family_member_id}
                onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                required
              >
                <option value={0}>Selecione o paciente...</option>
                {members.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Médico */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Médico *</label>
                <input
                  type="text"
                  value={formData.doctor_name}
                  onChange={(e) => setFormData({...formData, doctor_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
              </div>

              {/* Especialidade */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Especialidade *</label>
                <input
                  type="text"
                  value={formData.specialty}
                  onChange={(e) => setFormData({...formData, specialty: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Ex: Cardiologia, Pediatria"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Data/Hora da Consulta */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data e Hora *</label>
                <DateTimeInput
                  value={formData.appointment_date}
                  onChange={(value) => setFormData({...formData, appointment_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              {/* Local */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Local</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Hospital, Clínica, etc."
                />
              </div>
            </div>

            {/* Motivo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Motivo da Consulta *</label>
              <textarea
                value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Descreva o motivo da consulta..."
                required
              />
            </div>

            {/* Diagnóstico */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Diagnóstico</label>
              <textarea
                value={formData.diagnosis}
                onChange={(e) => setFormData({...formData, diagnosis: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Diagnóstico médico..."
              />
            </div>

            {/* Prescrição */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prescrição</label>
              <textarea
                value={formData.prescription}
                onChange={(e) => setFormData({...formData, prescription: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Medicamentos e orientações..."
              />
            </div>

            {/* Próxima Consulta */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Próxima Consulta</label>
              <DateTimeInput
                value={formData.next_appointment}
                onChange={(value) => setFormData({...formData, next_appointment: value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Informações adicionais..."
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
                className="w-full sm:w-auto px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal de Criar */}
      <Modal isOpen={isModalOpen} onClose={closeModal} title="Nova Consulta">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          <div className="sticky top-0 bg-white border-b border-gray-200 px-4 md:px-6 py-4 flex items-center justify-between z-10">
            <h3 className="text-lg md:text-xl font-semibold text-gray-900">
              Nova Consulta
            </h3>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5 md:h-6 md:w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-4 md:p-6 space-y-4 md:space-y-6 overflow-y-auto flex-1">
            {/* Paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
              <select
                value={formData.family_member_id}
                onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                required
              >
                <option value={0}>Selecione o paciente...</option>
                {members.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Médico */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Médico *</label>
                <input
                  type="text"
                  value={formData.doctor_name}
                  onChange={(e) => setFormData({...formData, doctor_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
              </div>

              {/* Especialidade */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Especialidade *</label>
                <input
                  type="text"
                  value={formData.specialty}
                  onChange={(e) => setFormData({...formData, specialty: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Ex: Cardiologia, Pediatria"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Data/Hora da Consulta */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data e Hora *</label>
                <DateTimeInput
                  value={formData.appointment_date}
                  onChange={(value) => setFormData({...formData, appointment_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              {/* Local */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Local</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Hospital, Clínica, etc."
                />
              </div>
            </div>

            {/* Motivo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Motivo da Consulta *</label>
              <textarea
                value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Descreva o motivo da consulta..."
                required
              />
            </div>

            {/* Diagnóstico */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Diagnóstico</label>
              <textarea
                value={formData.diagnosis}
                onChange={(e) => setFormData({...formData, diagnosis: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Diagnóstico médico..."
              />
            </div>

            {/* Prescrição */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prescrição</label>
              <textarea
                value={formData.prescription}
                onChange={(e) => setFormData({...formData, prescription: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Medicamentos e orientações..."
              />
            </div>

            {/* Próxima Consulta */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Próxima Consulta</label>
              <DateTimeInput
                value={formData.next_appointment}
                onChange={(value) => setFormData({...formData, next_appointment: value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Informações adicionais..."
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
                className="w-full sm:w-auto px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Criar Consulta
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  )
}
