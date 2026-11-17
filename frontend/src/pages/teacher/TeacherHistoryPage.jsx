import { ChevronRight, History } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { pollsApi } from '../../api/services'
import { EmptyState, ErrorAlert, LoadingBlock, StatusTag } from '../../components/common'
import { formatDateTime, pluralize } from '../../lib/format'
import { useTeacherRoom } from './TeacherLayout'

export function TeacherHistoryPage() {
  const { room } = useTeacherRoom()
  const [status, setStatus] = useState('COMPLETED')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!room) return
    setData(null)
    pollsApi.list(room.id, { status, page, limit: 20 }).then(setData).catch(setError)
  }, [room, status, page])

  return (
    <div style={{ maxWidth: 960 }}>
      <div className="page-head">
        <h1>Past polls</h1>
        <span className="spacer" />
        <div className="segmented" role="group" aria-label="Filter polls">
          {['COMPLETED', 'CANCELLED'].map((s) => (
            <button key={s} type="button" aria-pressed={status === s} onClick={() => { setStatus(s); setPage(1) }}>
              {s === 'COMPLETED' ? 'Ended' : 'Cancelled'}
            </button>
          ))}
        </div>
      </div>
      <ErrorAlert error={error} />
      {!data ? (
        <LoadingBlock />
      ) : data.items.length === 0 ? (
        <div className="list-card">
          <EmptyState icon={History} title={status === 'COMPLETED' ? 'No ended polls yet' : 'No cancelled polls'}>
            {status === 'COMPLETED' && 'Once you end a poll, its results and AI insights stay here.'}
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="list-card">
            {data.items.map((p) => (
              <div className="list-row" key={p.id}>
                <Link to={`/teach/polls/${p.id}`} className="row-link grow">
                  <h3>{p.title}</h3>
                  <p className="meta">
                    {pluralize(p.question_count, 'question')} · {formatDateTime(p.ended_at || p.cancelled_at)}
                  </p>
                </Link>
                <StatusTag status={p.status} />
                <Link to={`/teach/polls/${p.id}`} className="btn btn-sm">
                  {p.status === 'COMPLETED' ? 'Results' : 'Details'} <ChevronRight size={16} aria-hidden="true" />
                </Link>
              </div>
            ))}
          </div>
          {data.pages > 1 && (
            <div className="pager">
              <button type="button" className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="meta">Page {page} of {data.pages}</span>
              <button type="button" className="btn btn-sm" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
