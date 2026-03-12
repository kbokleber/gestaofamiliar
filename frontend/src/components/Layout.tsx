import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { 
  Home, Users, Calendar, Pill, Wrench, Settings, LogOut, 
  Heart, Menu, X, Activity, Shield, Building2, User, Wallet, TrendingUp
} from 'lucide-react'
import { useState } from 'react'
import { APP_VERSION } from '../config/version'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { 
      name: 'Saúde', 
      icon: Heart,
      children: [
        { name: 'Membros da Família', href: '/healthcare/members', icon: Users },
        { name: 'Consultas', href: '/healthcare/appointments', icon: Calendar },
        { name: 'Procedimentos', href: '/healthcare/procedures', icon: Activity },
        { name: 'Medicamentos', href: '/healthcare/medications', icon: Pill },
      ]
    },
    {
      name: 'Manutenção',
      icon: Wrench,
      children: [
        { name: 'Equipamentos', href: '/maintenance/equipment', icon: Settings },
        { name: 'Ordens de Manutenção', href: '/maintenance/orders', icon: Wrench },
      ]
    },
    {
      name: 'Finanças',
      icon: Wallet,
      children: [
        { name: 'Painel Geral', href: '/finance', icon: TrendingUp },
        { name: 'Lançamentos', href: '/finance/entries', icon: Wallet },
        { name: 'Recorrências', href: '/finance/recurrences', icon: Calendar },
        { name: 'Categorias', href: '/finance/categories', icon: Settings },
      ]
    },
  ]

  // Adicionar menu de admin se for superuser (apenas admins, não staff)
  const isAdmin = user?.is_superuser
  const adminNavigation = isAdmin ? [{
    name: 'Administração',
    icon: Shield,
    children: [
      { name: 'Usuários', href: '/admin/users', icon: Users },
      { name: 'Famílias', href: '/admin/families', icon: Building2 },
    ]
  }] : []

  const allNavigation = [...navigation, ...adminNavigation]

  return (
    <div className="min-h-screen overflow-x-hidden bg-gray-50">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-0 left-0 right-0 bg-white shadow-sm z-50 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Gestão Familiar</h1>
          <p className="text-xs text-gray-500">v{APP_VERSION}</p>
        </div>
        <button
          type="button"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
          aria-label={sidebarOpen ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={sidebarOpen}
        >
          {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        aria-label="Navegação principal" 
        className={`
          fixed left-0 z-40 flex bg-white shadow-lg transition-transform duration-200 ease-in-out
          top-16 h-[calc(100dvh-4rem)] w-[min(20rem,calc(100vw-1.5rem))]
          rounded-r-2xl border-r border-gray-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:top-0 lg:h-screen lg:w-64 lg:translate-x-0 lg:rounded-none lg:border-r
          flex-col
        `}
      >
        <div className="hidden border-b border-gray-100 p-6 lg:block">
          <h1 className="text-xl font-bold text-gray-900">Gestão Familiar</h1>
          <p className="mt-0.5 text-xs text-gray-500">v{APP_VERSION}</p>
          <p className="mt-1 text-sm text-gray-600">
            {user?.first_name && user?.last_name
              ? `${user.first_name} ${user.last_name}`.trim()
              : user?.first_name || user?.last_name || user?.username}
          </p>
        </div>

        <div className="border-b border-gray-100 px-4 py-4 lg:hidden">
          <p className="text-sm font-semibold text-gray-900">
            {user?.first_name && user?.last_name
              ? `${user.first_name} ${user.last_name}`.trim()
              : user?.first_name || user?.last_name || user?.username}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">Menu principal</p>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {allNavigation.map((item) => (
            <div key={item.name}>
              {item.children ? (
                <div className="space-y-1">
                  <div className="flex items-center px-3 py-2 text-sm font-medium text-gray-700">
                    <item.icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </div>
                  <div className="ml-4 space-y-1">
                    {item.children.map((child) => (
                      <Link
                        key={child.href}
                        to={child.href}
                        onClick={() => setSidebarOpen(false)}
                        className="flex items-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 rounded-md transition-colors"
                      >
                        <child.icon className="mr-3 h-4 w-4" />
                        {child.name}
                      </Link>
                    ))}
                  </div>
                </div>
              ) : (
                <Link
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-md transition-colors"
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )}
            </div>
          ))}
        </nav>

        <div className="shrink-0 border-t border-gray-100 bg-white p-4 space-y-1">
          <Link
            to="/profile"
            onClick={() => setSidebarOpen(false)}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 rounded-md transition-colors"
          >
            <User className="mr-3 h-5 w-5" />
            Meu Perfil
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
            aria-label="Sair da conta"
          >
            <LogOut className="mr-3 h-5 w-5" />
            Sair
          </button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="min-h-screen pt-16 lg:ml-64 lg:pt-0">
        <div className="p-4 sm:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

