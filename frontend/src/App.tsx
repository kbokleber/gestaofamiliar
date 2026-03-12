import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
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

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route path="/" element={<Dashboard />} />
        
        {/* Healthcare Routes */}
        <Route path="/healthcare/members" element={<FamilyMembers />} />
        <Route path="/healthcare/appointments" element={<Appointments />} />
        <Route path="/healthcare/appointments-test" element={<AppointmentsTest />} />
        <Route path="/healthcare/procedures" element={<Procedures />} />
        <Route path="/healthcare/medications" element={<Medications />} />
        
        {/* Maintenance Routes */}
        <Route path="/maintenance/equipment" element={<Equipment />} />
        <Route path="/maintenance/orders" element={<MaintenanceOrders />} />
        
        {/* Profile / Settings */}
        <Route path="/profile" element={<UserProfile />} />
        
        {/* Finance Routes */}
        <Route path="/finance" element={<FinanceDashboard />} />
        <Route path="/finance/entries" element={<FinanceEntries />} />
        <Route path="/finance/recurrences" element={<FinanceRecurrences />} />
        <Route path="/finance/categories" element={<FinanceCategories />} />
        
        {/* Admin Routes */}
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/families" element={<AdminFamilies />} />
      </Route>
    </Routes>
  )
}

export default App

