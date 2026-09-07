import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { App as AntApp } from 'antd'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ThemeProvider } from './theme/ThemeContext'
import AppLayout from './layout/AppLayout'
import LoginPage from './pages/LoginPage'
import DocumentsPage from './pages/DocumentsPage'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import type { ReactNode } from 'react'

function PrivateRoute({ children }: { children: ReactNode }) {
  const { auth } = useAuth()
  if (!auth?.access_token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <ThemeProvider>
      <AntApp>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/"
                element={
                  <PrivateRoute>
                    <AppLayout />
                  </PrivateRoute>
                }
              >
                <Route index element={<Navigate to="/chat" replace />} />
                <Route path="chat" element={<ChatPage />} />
                <Route path="docs" element={<DocumentsPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </AntApp>
    </ThemeProvider>
  )
}
