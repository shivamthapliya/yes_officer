import { BookOpen, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { historyApi } from '../../api/services'
import { EmptyState, ErrorAlert, LoadingBlock } from '../../components/common'
import { formatDateTime, pluralize } from '../../lib/format'

export function MyPollsPage() {
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setData(null)
    historyApi.myPolls({ page }).then(setData).catch(setError)
  }, [page])

  return (
    <div style={{ maxWidth: 960 }}>
      <div className="page-head">
        <h1>My polls</h1>
      </div>
      <ErrorAlert error={error} />
      {!data ? (
        <LoadingBlock />
      ) : data.items.length === 0 ? (
        <div className="list-card">
          <EmptyState
            icon={BookOpen}
            title="No polls yet"
            action={<Link to="/rooms" className="btn btn-primary">Go to your rooms</Link>}
          >
            Polls you take part in show up here once they end, so you can compare your answers with the correct ones.
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="list-card">
            {data.items.map((p) => (
              <div className="list-row" key={p.poll_id}>
                <Link to={`/history/${p.poll_id}`} className="row-link grow">
                  <h3>{p.title}</h3>
                  <p className="meta">
                    {p.room_name} · {p.teacher_name} · {pluralize(p.question_count, 'question')} · {formatDateTime(p.ended_at)}
                  </p>
                </Link>
                <Link to={`/history/${p.poll_id}`} className="btn btn-sm">
                  Review <ChevronRight size={16} aria-hidden="true" />
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
