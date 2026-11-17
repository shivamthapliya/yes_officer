import { Ban } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { pollsApi } from '../../api/services'
import { EmptyState, ErrorAlert, LoadingBlock, StatusTag } from '../../components/common'
import { InsightsPanel } from '../../components/InsightsPanel'
import { ResultsBoard } from '../../components/ResultsBoard'
import { useRoomEvent } from '../../context/RoomLiveContext'
import { useInsightsDisplay } from '../../hooks/useInsightsDisplay'
import { formatDateTime, pluralize } from '../../lib/format'
import { BackLink } from '../../components/BackLink'

export function PollReportPage() {
  const { pollId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [poll, setPoll] = useState(null)
  const [results, setResults] = useState(location.state?.results ?? null)
  const [error, setError] = useState(null)
  const [questionFilter, setQuestionFilter] = useState('')
  const insights = useInsightsDisplay()
  const filterRef = useRef('')

  const fetchInsights = useCallback(
    async (reset) => {
      const res = await pollsApi.insights(pollId, filterRef.current || undefined)
      const snap = { version: res.version, insights: res.insights, analysis_status: res.analysis_status }
      if (reset) insights.reset(snap)
      else insights.push(snap)
    },
    [pollId], // eslint-disable-line react-hooks/exhaustive-deps
  )

  useEffect(() => {
    pollsApi
      .detail(pollId)
      .then((detail) => {
        if (detail.status === 'DRAFT') return navigate(`/teach/polls/${pollId}/edit`, { replace: true })
        if (detail.status === 'ACTIVE') return navigate(`/teach/polls/${pollId}/live`, { replace: true })
        setPoll(detail)
        if (detail.status === 'COMPLETED') {
          pollsApi.results(pollId).then(setResults).catch(setError)
          fetchInsights(true).catch(() => {})
        }
        return null
      })
      .catch(setError)
  }, [pollId]) // eslint-disable-line react-hooks/exhaustive-deps

  useRoomEvent((e) => {
    if (e.type === 'insights_updated' && e.poll_id === pollId && e.version > insights.latestVersion.current) {
      fetchInsights(false).catch(() => {})
    }
  })

  const changeFilter = (value) => {
    setQuestionFilter(value)
    filterRef.current = value
    fetchInsights(true).catch(() => {})
  }

  if (!poll) return error ? <ErrorAlert error={error} /> : <LoadingBlock />

  return (
    <div>
      <BackLink to="/teach">My room</BackLink>
      <div className="page-head">
        <h1>{poll.title}</h1>
        <StatusTag status={poll.status} />
        <span className="spacer" />
        <span className="meta">
          {poll.ended_at && `Ended ${formatDateTime(poll.ended_at)}`}
          {poll.cancelled_at && `Cancelled ${formatDateTime(poll.cancelled_at)}`}
        </span>
      </div>
      <ErrorAlert error={error} />
      {poll.status === 'CANCELLED' ? (
        <div className="list-card">
          <EmptyState icon={Ban} title="This poll was cancelled">
            Cancelled polls keep no answers, results or AI insights.
          </EmptyState>
        </div>
      ) : (
        <div className="room-grid">
          <div>
            {results ? (
              <>
                <p className="muted" style={{ marginBottom: 'var(--s-4)' }}>
                  {pluralize(results.participant_count, 'student')} took part.
                </p>
                <ResultsBoard results={results} />
              </>
            ) : (
              <LoadingBlock label="Loading results…" />
            )}
          </div>
          <div className="report-side">
            <label className="field">
              <span>Insights for</span>
              <select className="select" value={questionFilter} onChange={(e) => changeFilter(e.target.value)}>
                <option value="">The whole poll</option>
                {poll.questions.map((q, i) => (
                  <option key={q.id} value={q.id}>
                    Q{i + 1}: {q.prompt.slice(0, 60)}
                  </option>
                ))}
              </select>
            </label>
            <InsightsPanel snapshot={insights.displayed} hasPending={insights.hasPending} questions={poll.questions} />
          </div>
        </div>
      )}
    </div>
  )
}
