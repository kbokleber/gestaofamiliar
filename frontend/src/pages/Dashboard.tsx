import { useState, useEffect } from 'react'
import { Heart, Users, Calendar, Settings, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import { isFutureDateTime } from '../utils/dateUtils'
import Loading from '../components/Loading'

interface DashboardStats {
  totalMembers: number
  totalAppointments: number
  totalEquipment: number
  activeMedications: number
  totalMaintenanceOrders: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalMembers: 0,
    totalAppointments: 0,
    totalEquipment: 0,
    activeMedications: 0,
    totalMaintenanceOrders: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const [membersRes, appointmentsRes, equipmentRes, medicationsRes, ordersRes] = await Promise.all([
        api.get('/healthcare/members'),
        api.get('/healthcare/appointments'),
        api.get('/maintenance/equipment'),
        api.get('/healthcare/medications', { params: { active_only: true } }),
        api.get('/maintenance/orders')
      ])

      // Filtrar apenas consultas futuras (sem problemas de timezone)
      const upcomingAppointments = appointmentsRes.data.filter((appointment: any) => {
        return isFutureDateTime(appointment.appointment_date)
      })

      setStats({
        totalMembers: membersRes.data.length,
        totalAppointments: upcomingAppointments.length,
        totalEquipment: equipmentRes.data.length,
        activeMedications: medicationsRes.data.length,
        totalMaintenanceOrders: ordersRes.data.length
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
      icon: Settings,
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
    {
      name: 'Ordens de Manutenção',
      value: loading ? '...' : stats.totalMaintenanceOrders.toString(),
      icon: Clock,
      href: '/maintenance/orders',
      color: 'bg-purple-500',
    },
  ]

  if (loading) {
    return <Loading message="Carregando dashboard..." />
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
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
    </div>
  )
}

