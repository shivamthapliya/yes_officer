import { ChevronRight, Radio } from 'lucide-react'
import { Fragment } from 'react'
import { Link, matchPath, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useTeacherRoom } from '../pages/teacher/TeacherLayout'

// Most specific patterns first. Each crumb is [label, href?]; the last one is the current page.
const TRAILS = [
  ['/teach/polls/:id/edit', [['My room', '/teach'], ['Edit poll']]],
  ['/teach/polls/:id/live', [['My room', '/teach'], ['Live poll']]],
  ['/teach/polls/:id', [['Past polls', '/teach/history'], ['Results']]],
  ['/teach/history', [['Past polls']]],
  ['/teach', [['My room']]],
  ['/rooms/:id', [['Rooms', '/rooms'], ['Room']]],
  ['/rooms', [['Rooms']]],
  ['/history/:id', [['My polls', '/history'], ['Review']]],
  ['/history', [['My polls']]],
]

const initials = (name = '') =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('') || '?'

export function TopBar() {
  const { pathname } = useLocation()
  const { user } = useAuth()
  const teacher = useTeacherRoom()
  const trail = TRAILS.find(([pattern]) => matchPath(pattern, pathname))?.[1] ?? []
  const livePollId = teacher?.activePollId
  const onLivePage = Boolean(livePollId) && pathname === `/teach/polls/${livePollId}/live`

  return (
    <header className="topbar">
      <nav className="crumbs" aria-label="Breadcrumb">
        <ol>
          {trail.map(([label, href], i) => (
            <Fragment key={label}>
              {i > 0 && (
                <li aria-hidden="true" className="crumb-sep">
                  <ChevronRight size={14} />
                </li>
              )}
              <li>
                {href && i < trail.length - 1 ? <Link to={href}>{label}</Link> : <span aria-current="page">{label}</span>}
              </li>
            </Fragment>
          ))}
        </ol>
      </nav>
      <span className="spacer" />
      {livePollId && !onLivePage && (
        <Link to={`/teach/polls/${livePollId}/live`} className="topbar-live">
          <Radio size={13} aria-hidden="true" /> LIVE <span className="topbar-live-cta">Open console</span>
        </Link>
      )}
      {user && (
        <span className="topbar-user">
          <span className="avatar" aria-hidden="true">{initials(user.full_name)}</span>
          <span className="topbar-user-text">
            <span className="topbar-name">{user.full_name}</span>
            <span className="topbar-role">{user.role === 'TEACHER' ? 'Teacher' : 'Student'}</span>
          </span>
        </span>
      )}
    </header>
  )
}
