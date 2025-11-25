import { useState, useEffect } from 'react'
import { Heart, Wrench, Users, Calendar } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

interface DashboardStats {
  totalMembers: number
  totalAppointments: number
  totalEquipment: number
  activeMedications: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalMembers: 0,
    totalAppointments: 0,
    totalEquipment: 0,
    activeMedications: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const [membersRes, appointmentsRes, equipmentRes, medicationsRes] = await Promise.all([
        api.get('/healthcare/members'),
        api.get('/healthcare/appointments'),
        api.get('/maintenance/equipment'),
        api.get('/healthcare/medications', { params: { active_only: true } })
      ])

      // Filtrar apenas consultas futuras
      const now = new Date()
      const upcomingAppointments = appointmentsRes.data.filter((appointment: any) => {
        const appointmentDate = new Date(appointment.appointment_date)
        return appointmentDate > now
      })

      setStats({
        totalMembers: membersRes.data.length,
        totalAppointments: upcomingAppointments.length,
        totalEquipment: equipmentRes.data.length,
        activeMedications: medicationsRes.data.length
      })
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const dashboardCards = [
    {
      name: 'Membros da Família',
      value: loading ? '...' : stats.totalMembers.toString(),
      icon: Users,
      href: '/healthcare/members',
      color: 'bg-blue-500',
    },
    {
      name: 'Próximas Consultas',
      value: loading ? '...' : stats.totalAppointments.toString(),
      icon: Calendar,
      href: '/healthcare/appointments',
      color: 'bg-green-500',
    },
    {
      name: 'Equipamentos',
      value: loading ? '...' : stats.totalEquipment.toString(),
      icon: Wrench,
      href: '/maintenance/equipment',
      color: 'bg-orange-500',
    },
    {
      name: 'Medicações Ativas',
      value: loading ? '...' : stats.activeMedications.toString(),
      icon: Heart,
      href: '/healthcare/medications',
      color: 'bg-red-500',
    },
  ]

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {dashboardCards.map((stat) => (
          <Link
            key={stat.name}
            to={stat.href}
            className="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className={`flex-shrink-0 rounded-md p-3 ${stat.color}`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.name}
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {stat.value}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Bem-vindo!</h2>
          <p className="text-gray-600">
            Este é o Gestão Familiar, uma plataforma completa para gerenciar a saúde da sua família e
            manutenção de equipamentos domésticos.
          </p>
          <div className="mt-4 space-y-2">
            <p className="text-sm text-gray-600">
              • Gerencie consultas médicas e medicamentos
            </p>
            <p className="text-sm text-gray-600">
              • Acompanhe a saúde de cada membro da família
            </p>
            <p className="text-sm text-gray-600">
              • Organize manutenções de equipamentos
            </p>
            <p className="text-sm text-gray-600">
              • Acesse de qualquer dispositivo
            </p>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Ações Rápidas</h2>
          <div className="space-y-3">
            <Link
              to="/healthcare/members"
              className="block w-full text-left px-4 py-3 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md transition-colors"
            >
              + Adicionar Membro da Família
            </Link>
            <Link
              to="/healthcare/appointments"
              className="block w-full text-left px-4 py-3 bg-green-50 hover:bg-green-100 text-green-700 rounded-md transition-colors"
            >
              + Nova Consulta
            </Link>
            <Link
              to="/maintenance/equipment"
              className="block w-full text-left px-4 py-3 bg-orange-50 hover:bg-orange-100 text-orange-700 rounded-md transition-colors"
            >
              + Registrar Equipamento
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

