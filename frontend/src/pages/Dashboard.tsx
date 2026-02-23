import { Heart, Users, Calendar, Settings, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import Loading from '../components/Loading'

interface DashboardStats {
  total_members: number
  total_appointments: number
  total_equipment: number
  active_medications: number
  total_orders: number
}

// Carregar dados do localStorage como placeholder
const getPlaceholderData = (): DashboardStats | undefined => {
  try {
    const cached = localStorage.getItem('dashboard-stats')
    return cached ? JSON.parse(cached) : undefined
  } catch {
    return undefined
  }
}

export default function Dashboard() {
  // Uma única requisição para todas as estatísticas do dashboard
  const { data: stats, isLoading: loading, isError: queryError, refetch } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await api.get('/dashboard/stats')
      try {
        localStorage.setItem('dashboard-stats', JSON.stringify(res.data))
      } catch { /* localStorage cheio, ignorar */ }
      return res.data
    },
    placeholderData: getPlaceholderData(),
    staleTime: 5 * 60 * 1000,
  })

  const dashboardCards = [
    {
      name: 'Membros da Família',
      value: stats?.total_members?.toString() ?? '...',
      icon: Users,
      href: '/healthcare/members',
      color: 'bg-blue-500',
    },
    {
      name: 'Próximas Consultas',
      value: stats?.total_appointments?.toString() ?? '...',
      icon: Calendar,
      href: '/healthcare/appointments',
      color: 'bg-green-500',
    },
    {
      name: 'Equipamentos',
      value: stats?.total_equipment?.toString() ?? '...',
      icon: Settings,
      href: '/maintenance/equipment',
      color: 'bg-orange-500',
    },
    {
      name: 'Medicações Ativas',
      value: stats?.active_medications?.toString() ?? '...',
      icon: Heart,
      href: '/healthcare/medications',
      color: 'bg-red-500',
    },
    {
      name: 'Ordens de Manutenção',
      value: stats?.total_orders?.toString() ?? '...',
      icon: Clock,
      href: '/maintenance/orders',
      color: 'bg-purple-500',
    },
  ]

  if (loading && !stats) {
    return <Loading message="Carregando dashboard..." />
  }

  if (queryError) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg" role="alert">
          <p className="font-medium">Erro ao carregar os dados.</p>
          <p className="text-sm mt-1">Tente novamente ou recarregue a página.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
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

