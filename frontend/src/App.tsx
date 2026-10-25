import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import AcessoNegado from './pages/AcessoNegado'
import { keycloakEnabled } from './lib/keycloak'
import Dashboard from './pages/Dashboard'
import FamilyMembers from './pages/healthcare/FamilyMembers'
import Appointments from './pages/healthcare/Appointments'
import AppointmentsTest from './pages/healthcare/AppointmentsTest'
import Procedures from './pages/healthcare/Procedures'
import Medications from './pages/healthcare/Medications'
import Equipment from './pages/maintenance/Equipment'
import MaintenanceOrders from './pages/maintenance/MaintenanceOrders'
import AdminUsers from './pages/admin/Users'
import AdminFamilies from './pages/admin/Families'
import UserProfile from './pages/profile/UserProfile'
import FinanceDashboard from './pages/finance/FinanceDashboard'
import FinanceEntries from './pages/finance/FinanceEntries'
import FinanceRecurrences from './pages/finance/FinanceRecurrences'
import FinanceCategories from './pages/finance/FinanceCategories'
import FinanceImportRules from './pages/finance/FinanceImportRules'
import Estudos, { SemMenu } from './pages/estudos/Estudos'
import { canSeeMenu, firstAllowedPath, type MenuKey } from './lib/menus'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function MenuRoute({ menu, children }: { menu: MenuKey; children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user)
  if (!canSeeMenu(user, menu)) {
    return <Navigate to={firstAllowedPath(user)} replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/acesso-negado" element={<AcessoNegado />} />
      <Route path="/register" element={keycloakEnabled ? <Navigate to="/login" replace /> : <Register />} />
      
      <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route path="/" element={<MenuRoute menu="dashboard"><Dashboard /></MenuRoute>} />
        <Route path="/sem-menu" element={<SemMenu />} />
        <Route path="/estudos" element={<MenuRoute menu="estudos"><Estudos /></MenuRoute>} />
        
        {/* Healthcare Routes */}
        <Route path="/healthcare/members" element={<MenuRoute menu="saude"><FamilyMembers /></MenuRoute>} />
        <Route path="/healthcare/appointments" element={<MenuRoute menu="saude"><Appointments /></MenuRoute>} />
        <Route path="/healthcare/appointments-test" element={<MenuRoute menu="saude"><AppointmentsTest /></MenuRoute>} />
        <Route path="/healthcare/procedures" element={<MenuRoute menu="saude"><Procedures /></MenuRoute>} />
        <Route path="/healthcare/medications" element={<MenuRoute menu="saude"><Medications /></MenuRoute>} />
        
        {/* Maintenance Routes */}
        <Route path="/maintenance/equipment" element={<MenuRoute menu="manutencao"><Equipment /></MenuRoute>} />
        <Route path="/maintenance/orders" element={<MenuRoute menu="manutencao"><MaintenanceOrders /></MenuRoute>} />
        
        {/* Profile / Settings */}
        <Route path="/profile" element={<UserProfile />} />
        
        {/* Finance Routes */}
        <Route path="/finance" element={<MenuRoute menu="financas"><FinanceDashboard /></MenuRoute>} />
        <Route path="/finance/entries" element={<MenuRoute menu="financas"><FinanceEntries /></MenuRoute>} />
        <Route path="/finance/recurrences" element={<MenuRoute menu="financas"><FinanceRecurrences /></MenuRoute>} />
        <Route path="/finance/categories" element={<MenuRoute menu="financas"><FinanceCategories /></MenuRoute>} />
        <Route path="/finance/import-category-rules" element={<MenuRoute menu="financas"><FinanceImportRules /></MenuRoute>} />
        
        {/* Admin Routes */}
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/families" element={<AdminFamilies />} />
      </Route>
    </Routes>
  )
}

export default App

