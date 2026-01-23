import { Heart, Users, Calendar, Settings, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { isFutureDateTime } from '../utils/dateUtils'
import Loading from '../components/Loading'

export default function Dashboard() {
  // Usar React Query para cache automático - dados ficam em cache por 5 min
  const { data: members = [], isLoading: loadingMembers } = useQuery({
    queryKey: ['healthcare-members'],
    queryFn: async () => {
      const res = await api.get('/healthcare/members')
      return res.data
    }
  })

  const { data: appointments = [], isLoading: loadingAppointments } = useQuery({
    queryKey: ['healthcare-appointments'],
    queryFn: async () => {
      const res = await api.get('/healthcare/appointments')
      return res.data
    }
  })

  const { data: equipment = [], isLoading: loadingEquipment } = useQuery({
    queryKey: ['maintenance-equipment'],
    queryFn: async () => {
      const res = await api.get('/maintenance/equipment')
      return res.data
    }
  })

  const { data: medications = [], isLoading: loadingMedications } = useQuery({
    queryKey: ['healthcare-medications-active'],
    queryFn: async () => {
      const res = await api.get('/healthcare/medications', { params: { active_only: true } })
      return res.data
    }
  })

  const { data: orders = [], isLoading: loadingOrders } = useQuery({
    queryKey: ['maintenance-orders'],
    queryFn: async () => {
      const res = await api.get('/maintenance/orders')
      return res.data
    }
  })

  const loading = loadingMembers || loadingAppointments || loadingEquipment || loadingMedications || loadingOrders

  // Filtrar apenas consultas futuras
  const upcomingAppointments = appointments.filter((appointment: any) => {
    return isFutureDateTime(appointment.appointment_date)
  })

  const stats = {
    totalMembers: members.length,
    totalAppointments: upcomingAppointments.length,
    totalEquipment: equipment.length,
    activeMedications: medications.length,
    totalMaintenanceOrders: orders.length
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

