import { useState, useEffect } from 'react'
import { Calendar, ArrowLeft } from 'lucide-react'
import api from '../../lib/api'
import { formatDateTimeBR } from '../../utils/dateUtils'
import { useNavigate } from 'react-router-dom'

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

export default function AppointmentsTest() {
  const navigate = useNavigate()
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Buscar consultas do endpoint normal
      const appointmentsResponse = await api.get('/healthcare/appointments')
      const appointmentsData = appointmentsResponse.data
      
      console.log('🔍 DADOS RECEBIDOS DA API:', appointmentsData)
      if (appointmentsData.length > 0) {
        console.log('📋 Primeira consulta:', appointmentsData[0])
        console.log('📅 appointment_date:', appointmentsData[0].appointment_date)
      }
      
      // Buscar membros
      const membersResponse = await api.get('/healthcare/members')
      const membersData = membersResponse.data
      setMembers(membersData)
      
      // Adicionar nome do membro em cada consulta
      const appointmentsWithMembers = appointmentsData.map((apt: Appointment) => ({
        ...apt,
        family_member: membersData.find((m: FamilyMember) => m.id === apt.family_member_id)
      }))
      
      setAppointments(appointmentsWithMembers)
    } catch (err: any) {
      console.error('Erro ao buscar dados:', err)
      setError('Erro ao carregar dados de teste')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/healthcare/appointments')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <Calendar className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Consultas Médicas - TESTE</h1>
              <p className="text-sm text-gray-500">Endpoint de teste para validar timezone</p>
            </div>
          </div>
        </div>
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Raw Data
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {appointments.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                      Nenhuma consulta encontrada
                    </td>
                  </tr>
                ) : (
                  appointments.map((appointment) => (
                    <tr key={appointment.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {appointment.family_member?.name || `Membro ${appointment.family_member_id}`}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 font-bold">
                          {formatDateTimeBR(appointment.appointment_date)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{appointment.doctor_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{appointment.specialty}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">{appointment.location || '-'}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs text-gray-500 font-mono">
                          {appointment.appointment_date}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="bg-blue-50 px-6 py-4 border-t border-blue-100">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">🔍 Informações de Debug:</h3>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• Endpoint: <code className="bg-blue-100 px-1 py-0.5 rounded">/api/v1/healthcare/appointments/test</code></li>
              <li>• Este endpoint retorna datetimes SEM timezone</li>
              <li>• Compare a coluna "Data/Hora" (formatada) com "Raw Data" (como veio da API)</li>
              <li>• Se estiver correto, a Data/Hora formatada deve ser igual ao horário no banco</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

