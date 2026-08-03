import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './components/ui/Toast'
import AppLayout from './components/layout/AppLayout'
import Spinner from './components/ui/Spinner'

import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Goals from './pages/Goals'
import GoalDetail from './pages/GoalDetail'
import NewGoal from './pages/NewGoal'
import Tasks from './pages/Tasks'
import Focus from './pages/Focus'
import Calendar from './pages/Calendar'
import Settings from './pages/Settings'
import Circles from './pages/Circles'
import CircleDetail from './pages/CircleDetail'
import NotFound from './pages/NotFound'

// Recharts and the PDF engine are the two heaviest dependencies and each is
// used by exactly one screen, so both load on demand rather than weighing down
// first paint.
const Analytics = lazy(() => import('./pages/Analytics'))
const Studio = lazy(() => import('./pages/Studio'))
const PublicRoadmap = lazy(() => import('./pages/PublicRoadmap'))

function FullPageSpinner() {
  return (
    <div className="grid min-h-screen place-items-center bg-canvas text-brand-600">
      <Spinner size={26} />
    </div>
  )
}

/** Spinner sized for the content area, inside the authenticated shell. */
function PageSpinner() {
  return (
    <div className="grid place-items-center py-24 text-brand-600">
      <Spinner size={24} />
    </div>
  )
}

function RequireAuth({ children }) {
  const { isAuthenticated, booting } = useAuth()
  const location = useLocation()

  if (booting) return <FullPageSpinner />
  if (!isAuthenticated) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return children
}

function RedirectIfAuthed({ children }) {
  const { isAuthenticated, booting } = useAuth()
  if (booting) return <FullPageSpinner />
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children
}

function AppRoutes() {
  // No AnimatePresence here: pages animate in via PageShell and define no exit
  // animation, and wrapping routes in `mode="wait"` stalls swaps whenever a
  // page owns its own presence children.
  return (
    <Routes>
        <Route
          path="/login"
          element={
            <RedirectIfAuthed>
              <Login />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/register"
          element={
            <RedirectIfAuthed>
              <Register />
            </RedirectIfAuthed>
          }
        />

        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/goals/new" element={<NewGoal />} />
          <Route path="/goals/:id" element={<GoalDetail />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/focus" element={<Focus />} />
          <Route
            path="/studio"
            element={
              <Suspense fallback={<PageSpinner />}>
                <Studio />
              </Suspense>
            }
          />
          <Route
            path="/analytics"
            element={
              <Suspense fallback={<PageSpinner />}>
                <Analytics />
              </Suspense>
            }
          />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/circles" element={<Circles />} />
          <Route path="/circles/:id" element={<CircleDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Public share link — deliberately outside the authenticated shell. */}
        <Route
          path="/r/:token"
          element={
            <Suspense fallback={<FullPageSpinner />}>
              <PublicRoadmap />
            </Suspense>
          }
        />

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
