import { ChevronRight, ClipboardList, Pencil, Plus, Radio, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { pollsApi, roomsApi } from '../../api/services'
import { ChatPanel } from '../../components/ChatPanel'
import { EmptyState, ErrorAlert, LoadingBlock, StatusTag } from '../../components/common'
import { useAuth } from '../../context/AuthContext'
import { useRoomEvent, useRoomLive } from '../../context/RoomLiveContext'
import { formatDateTime, formatDuration, pluralize } from '../../lib/format'
import { useTeacherRoom } from './TeacherLayout'

function RoomName({ room, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(room.name)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      onSaved(await roomsApi.renameMine(name))
      setEditing(false)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  if (!editing) {
    return (
      <>
        <h1>{room.name}</h1>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setName(room.name); setEditing(true) }}>
          <Pencil size={15} aria-hidden="true" /> Rename
        </button>
      </>
    )
  }
  return (
    <form className="inline-edit" onSubmit={save}>
      <label className="sr-only" htmlFor="room-name">Room name</label>
      <input id="room-name" className="input" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} autoFocus />
      <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !name.trim()}>Save</button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditing(false)}>Cancel</button>
      {error && <ErrorAlert error={error} />}
    </form>
  )
}

function PollRow({ poll }) {
  const target = poll.status === 'DRAFT' ? `/teach/polls/${poll.id}/edit` : poll.status === 'ACTIVE' ? `/teach/polls/${poll.id}/live` : `/teach/polls/${poll.id}`
  return (
    <div className="list-row">
      <Link to={target} className="row-link grow">
        <h3>{poll.title}</h3>
        <p className="meta">
          {pluralize(poll.question_count, 'question')} · {formatDuration(poll.time_limit_seconds)}
          {poll.ended_at ? ` · ended ${formatDateTime(poll.ended_at)}` : ` · edited ${formatDateTime(poll.updated_at)}`}
        </p>
      </Link>
      <StatusTag status={poll.status} />
      <Link to={target} className="btn btn-sm" aria-label={`Open ${poll.title}`}>
        {poll.status === 'DRAFT' ? 'Edit' : poll.status === 'ACTIVE' ? 'Open console' : 'Results'}
        <ChevronRight size={16} aria-hidden="true" />
      </Link>
    </div>
  )
}

export function TeacherRoomPage() {
  const { user } = useAuth()
  const { room, setRoomState, activePollId } = useTeacherRoom()
  const live = useRoomLive()
  const navigate = useNavigate()
  const [polls, setPolls] = useState(null)
  const [error, setError] = useState(null)
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    if (!room) return
    pollsApi.list(room.id).then((page) => setPolls(page.items)).catch(setError)
  }, [room])

  useEffect(load, [load])
  useRoomEvent((e) => {
    if (['poll_started', 'poll_ended', 'poll_cancelled'].includes(e.type)) load()
  })

  const createPoll = async () => {
    setCreating(true)
    try {
      const poll = await pollsApi.create(room.id, { title: 'Untitled poll', time_limit_seconds: 120 })
      navigate(`/teach/polls/${poll.id}/edit`)
    } catch (err) {
      setError(err)
      setCreating(false)
    }
  }

  if (!room) return <LoadingBlock />

  const drafts = polls?.filter((p) => p.status === 'DRAFT') ?? []
  const ended = polls?.filter((p) => p.status === 'COMPLETED' || p.status === 'CANCELLED').slice(0, 5) ?? []
  const active = polls?.find((p) => p.status === 'ACTIVE')

  return (
    <div className="room-grid">
      <div>
        <div className="page-head">
          <RoomName room={room} onSaved={setRoomState} />
          <span className="spacer" />
          <span className="meta">
            <Users size={14} aria-hidden="true" style={{ verticalAlign: '-2px' }} /> {pluralize(room.participant_count, 'student')} joined
          </span>
          <button type="button" className="btn btn-primary" onClick={createPoll} disabled={creating}>
            <Plus size={18} aria-hidden="true" /> New poll
          </button>
        </div>
        <ErrorAlert error={error} />

        {(active || activePollId) && (
          <div className="live-banner">
            <span className="live-pill"><span className="dot" />LIVE</span>
            <h2>{active?.title ?? 'A poll is running'}</h2>
            <Link className="btn btn-primary" to={`/teach/polls/${active?.id ?? activePollId}/live`}>
              <Radio size={17} aria-hidden="true" /> Open live console
            </Link>
          </div>
        )}

        {polls === null ? (
          <LoadingBlock label="Loading polls…" />
        ) : polls.length === 0 ? (
          <div className="list-card">
            <EmptyState
              icon={ClipboardList}
              title="No polls yet"
              action={
                <button type="button" className="btn btn-primary" onClick={createPoll} disabled={creating}>
                  <Plus size={18} aria-hidden="true" /> Write your first poll
                </button>
              }
            >
              Draft a few multiple-choice questions, then start the poll when your class is in the room. Students who
              have joined can answer one question at a time.
            </EmptyState>
          </div>
        ) : (
          <>
            <h2 className="section-title">Drafts</h2>
            {drafts.length ? (
              <div className="list-card">{drafts.map((p) => <PollRow key={p.id} poll={p} />)}</div>
            ) : (
              <p className="muted">No drafts. Use “New poll” to write one.</p>
            )}
            <h2 className="section-title">
              Recent polls <span className="spacer" style={{ flex: 1 }} />
              <Link to="/teach/history" className="btn btn-ghost btn-sm">See all</Link>
            </h2>
            {ended.length ? (
              <div className="list-card">{ended.map((p) => <PollRow key={p.id} poll={p} />)}</div>
            ) : (
              <p className="muted">Polls you run will appear here with their results.</p>
            )}
          </>
        )}
      </div>
      <ChatPanel
        messages={live.messages}
        onSend={live.send}
        status={live.status}
        online={live.online.length}
        currentUserId={user.id}
      />
    </div>
  )
}
