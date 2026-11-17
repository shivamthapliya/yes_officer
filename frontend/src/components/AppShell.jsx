import { BookOpen, DoorOpen, History, LayoutGrid, LogOut, Radio } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { BrandMark } from './BrandMark'

function RailLink({ to, icon: Icon, label, short, end, badge }) {
  return (
    <NavLink to={to} end={end} className="rail-link">
      <Icon size={18} aria-hidden="true" />
      <span>
        {short ? (
          <>
            <span className="label-long">{label}</span>
            <span className="sr-only">{label}</span>
          </>
        ) : (
          label
        )}
      </span>
      {badge}
    </NavLink>
  )
}

export function AppShell({ liveBadge = null }) {
  const { user, logout } = useAuth()
  const isTeacher = user?.role === 'TEACHER'

  return (
    <div className="shell">
      <nav className="rail" aria-label="Main">
        <NavLink to={isTeacher ? '/teach' : '/rooms'} className="brand">
          <BrandMark size={38} />
          <span className="brand-text">Yes Officer</span>
        </NavLink>
        {isTeacher ? (
          <>
            <RailLink to="/teach" end icon={LayoutGrid} label="My room" badge={liveBadge} />
            <RailLink to="/teach/history" icon={History} label="Past polls" short />
          </>
        ) : (
          <>
            <RailLink to="/rooms" end icon={DoorOpen} label="Rooms" />
            <RailLink to="/history" icon={BookOpen} label="My polls" />
          </>
        )}
        <div className="rail-foot">
          <span className="rail-user">{user?.full_name}</span>
          <span className="rail-role">{isTeacher ? 'TEACHER' : 'STUDENT'}</span>
          <button type="button" className="btn btn-sm" onClick={logout} aria-label="Sign out">
            <LogOut size={16} aria-hidden="true" />
            <span className="signout-label">Sign out</span>
          </button>
        </div>
      </nav>
      <main className="main" id="main">
        <Outlet />
      </main>
    </div>
  )
}

export function LiveBadge() {
  return (
    <span className="rail-live" title="A poll is live">
      <Radio size={11} aria-hidden="true" style={{ verticalAlign: '-1px' }} /> LIVE
    </span>
  )
}
