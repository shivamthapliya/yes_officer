import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { LoadingBlock } from './components/common'
import { useAuth } from './context/AuthContext'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { MyPollsPage } from './pages/student/MyPollsPage'
import { ReviewPage } from './pages/student/ReviewPage'
import { RoomsPage } from './pages/student/RoomsPage'
import { StudentRoomPage } from './pages/student/StudentRoomPage'
import { LiveConsolePage } from './pages/teacher/LiveConsolePage'
import { PollEditorPage } from './pages/teacher/PollEditorPage'
import { PollReportPage } from './pages/teacher/PollReportPage'
import { TeacherHistoryPage } from './pages/teacher/TeacherHistoryPage'
import { TeacherLayout } from './pages/teacher/TeacherLayout'
import { TeacherRoomPage } from './pages/teacher/TeacherRoomPage'

const homeFor = (user) => (user?.role === 'TEACHER' ? '/teach' : '/rooms')

function RequireRole({ role }) {
  const { status, user } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <LoadingBlock />
  if (status !== 'authenticated') return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.role !== role) return <Navigate to={homeFor(user)} replace />
  return <Outlet />
}

function GuestOnly() {
  const { status, user } = useAuth()
  if (status === 'loading') return <LoadingBlock />
  if (status === 'authenticated') return <Navigate to={homeFor(user)} replace />
  return <Outlet />
}

function Home() {
  const { status, user } = useAuth()
  if (status === 'loading') return <LoadingBlock />
  return <Navigate to={status === 'authenticated' ? homeFor(user) : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireRole role="TEACHER" />}>
        <Route path="/teach" element={<TeacherLayout />}>
          <Route index element={<TeacherRoomPage />} />
          <Route path="history" element={<TeacherHistoryPage />} />
          <Route path="polls/:pollId/edit" element={<PollEditorPage />} />
          <Route path="polls/:pollId/live" element={<LiveConsolePage />} />
          <Route path="polls/:pollId" element={<PollReportPage />} />
        </Route>
      </Route>
      <Route element={<RequireRole role="STUDENT" />}>
        <Route element={<AppShell />}>
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/rooms/:roomId" element={<StudentRoomPage />} />
          <Route path="/history" element={<MyPollsPage />} />
          <Route path="/history/:pollId" element={<ReviewPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
