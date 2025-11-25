import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { 
  Home, Users, Calendar, Pill, Wrench, Settings, LogOut, 
  Heart, Menu, X, Activity, Shield
} from 'lucide-react'
import { useState } from 'react'

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
  ]

  // Adicionar menu de admin se for superuser ou staff
  const isAdmin = user?.is_superuser || user?.is_staff
  const adminNavigation = isAdmin ? [{
    name: 'Administração',
    icon: Shield,
    children: [
      { name: 'Usuários', href: '/admin/users', icon: Users },
    ]
  }] : []

  const allNavigation = [...navigation, ...adminNavigation]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-0 left-0 right-0 bg-white shadow-sm z-50 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Gestão Familiar</h1>
          <p className="text-xs text-gray-500">v1.0</p>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="text-gray-600 hover:text-gray-900"
        >
          {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside 
        className={`
          fixed top-0 left-0 h-full w-64 bg-white shadow-lg transform transition-transform duration-200 ease-in-out z-40
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
      >
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-900">Gestão Familiar</h1>
          <p className="text-xs text-gray-500 mt-0.5">v1.0</p>
          <p className="text-sm text-gray-600 mt-1">Olá, {user?.first_name || user?.username}!</p>
        </div>

        <nav className="px-3 mt-6 space-y-1">
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

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors"
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
      <main className="lg:ml-64 pt-16 lg:pt-0 min-h-screen">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

