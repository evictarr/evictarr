import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './api/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Profile } from './pages/Profile'
import { IntegrationsSettings } from './pages/Settings/Integrations'
import { Rules } from './pages/Rules'
import { History } from './pages/History'
import { PendingDeletions } from './pages/PendingDeletions'
import { GeneralSettings } from './pages/Settings/General'
import { NotificationsSettings } from './pages/Settings/Notifications'
import { SecuritySettings } from './pages/Settings/Security'
import { OrphanedFiles } from './pages/OrphanedFiles'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status, authMethod } = useAuth()

  if (status === 'loading' || authMethod === 'loading') {
    return null
  }
  if (authMethod === 'basic' && status !== 'signed-in') {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function LoginRoute() {
  const { status, authMethod } = useAuth()
  if (authMethod === 'none' || status === 'signed-in') {
    return <Navigate to="/" replace />
  }
  return <Login />
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginRoute />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="rules" element={<Rules />} />
            <Route path="pending-deletions" element={<PendingDeletions />} />
            <Route path="history" element={<History />} />
            <Route path="orphaned-files" element={<OrphanedFiles />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings/integrations" element={<IntegrationsSettings />} />
            <Route path="settings/general" element={<GeneralSettings />} />
            <Route path="settings/notifications" element={<NotificationsSettings />} />
            <Route path="settings/security" element={<SecuritySettings />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
