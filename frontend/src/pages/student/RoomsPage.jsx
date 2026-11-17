import { DoorOpen, Search, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { roomsApi } from '../../api/services'
import { EmptyState, ErrorAlert, LoadingBlock } from '../../components/common'
import { pluralize } from '../../lib/format'

function RoomCard({ room, onJoin, joining }) {
  return (
    <article className="room-card">
      {room.has_active_poll ? <span className="tab-label live">LIVE POLL</span> : room.is_joined && <span className="tab-label">JOINED</span>}
      <h3>{room.name}</h3>
      <p className="muted">{room.teacher_name}</p>
      <div className="foot">
        <span className="meta">
          <Users size={13} aria-hidden="true" style={{ verticalAlign: '-2px' }} /> {pluralize(room.participant_count, 'student')}
        </span>
        {room.is_joined ? (
          <Link className="btn btn-primary btn-sm" to={`/rooms/${room.id}`}>Enter room</Link>
        ) : (
          <button type="button" className="btn btn-sm" onClick={() => onJoin(room)} disabled={joining === room.id}>
            {joining === room.id && <span className="spinner" aria-hidden="true" />}
            Join room
          </button>
        )}
      </div>
    </article>
  )
}

export function RoomsPage() {
  const navigate = useNavigate()
  const [joined, setJoined] = useState(null)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [browse, setBrowse] = useState(null)
  const [error, setError] = useState(null)
  const [joining, setJoining] = useState(null)

  useEffect(() => {
    roomsApi.joined().then(setJoined).catch(setError)
  }, [])

  useEffect(() => {
    setBrowse(null)
    roomsApi.list({ search: query, page }).then(setBrowse).catch(setError)
  }, [query, page])

  const join = async (room) => {
    setJoining(room.id)
    try {
      await roomsApi.join(room.id)
      navigate(`/rooms/${room.id}`)
    } catch (err) {
      setError(err)
      setJoining(null)
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>Rooms</h1>
      </div>
      <ErrorAlert error={error} />

      <h2 className="section-title">Your rooms</h2>
      {joined === null ? (
        <LoadingBlock />
      ) : joined.length === 0 ? (
        <p className="muted" style={{ marginBottom: 'var(--s-4)' }}>
          You haven’t joined a room yet. Find your teacher below and join their room.
        </p>
      ) : (
        <div className="room-cards" style={{ marginTop: 'var(--s-5)' }}>
          {joined.map((r) => <RoomCard key={r.id} room={r} />)}
        </div>
      )}

      <h2 className="section-title" style={{ marginTop: 'var(--s-7)' }}>Find a room</h2>
      <form className="search-bar" role="search" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(search.trim()) }}>
        <label htmlFor="room-search" className="sr-only">Search by room or teacher name</label>
        <input
          id="room-search"
          className="input"
          type="search"
          placeholder="Room or teacher name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="btn">
          <Search size={17} aria-hidden="true" /> Search
        </button>
      </form>
      {browse === null ? (
        <LoadingBlock />
      ) : browse.items.length === 0 ? (
        <div className="list-card">
          <EmptyState icon={DoorOpen} title={query ? `No rooms match “${query}”` : 'No rooms yet'}>
            {query ? 'Check the spelling, or search by your teacher’s name instead.' : 'Rooms appear once teachers sign up.'}
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="room-cards" style={{ marginTop: 'var(--s-5)' }}>
            {browse.items.map((r) => <RoomCard key={r.id} room={r} onJoin={join} joining={joining} />)}
          </div>
          {browse.pages > 1 && (
            <div className="pager">
              <button type="button" className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="meta">Page {page} of {browse.pages}</span>
              <button type="button" className="btn btn-sm" disabled={page >= browse.pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
