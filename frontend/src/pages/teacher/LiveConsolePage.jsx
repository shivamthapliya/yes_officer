import { ChevronRight, Flag, Trophy, XCircle } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { pollsApi } from '../../api/services'
import { ChatPanel } from '../../components/ChatPanel'
import { ConfirmDialog, ErrorAlert, LoadingBlock } from '../../components/common'
import { InsightsPanel } from '../../components/InsightsPanel'
import { DrawerStrip, OptionRow, QuestionCard } from '../../components/QuestionCard'
import { FirstCorrectToast } from '../../components/ResultsBoard'
import { useAuth } from '../../context/AuthContext'
import { useRoomEvent, useRoomLive } from '../../context/RoomLiveContext'
import { useToast } from '../../context/ToastContext'
import { useCountdown } from '../../hooks/useCountdown'
import { useInsightsDisplay } from '../../hooks/useInsightsDisplay'
import { useTeacherRoom } from './TeacherLayout'

export function LiveConsolePage() {
  const { pollId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const room = useRoomLive()
  const { setActivePollId } = useTeacherRoom()
  const [poll, setPoll] = useState(null)
  const [live, setLive] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [scope, setScope] = useState('question')
  const insights = useInsightsDisplay()
  const scopeRef = useRef({ scope, questionId: null })

  const fetchInsights = useCallback(
    async ({ reset = false } = {}) => {
      const { scope: s, questionId } = scopeRef.current
      try {
        const res = await pollsApi.insights(pollId, s === 'question' ? questionId : undefined)
        const snapshot = { version: res.version, insights: res.insights, analysis_status: res.analysis_status }
        if (reset) insights.reset(snapshot)
        else insights.push(snapshot)
      } catch {
        /* insights are supplementary; the console keeps working */
      }
    },
    [pollId, insights.push, insights.reset], // eslint-disable-line react-hooks/exhaustive-deps
  )

  const loadLive = useCallback(async () => {
    const state = await pollsApi.live(pollId)
    if (state.status === 'COMPLETED') return navigate(`/teach/polls/${pollId}`, { replace: true })
    if (state.status !== 'ACTIVE') return navigate(state.status === 'DRAFT' ? `/teach/polls/${pollId}/edit` : '/teach', { replace: true })
    setLive(state)
    scopeRef.current.questionId = state.current_question?.id ?? null
    return state
  }, [pollId, navigate])

  useEffect(() => {
    Promise.all([pollsApi.detail(pollId), loadLive()])
      .then(([detail]) => {
        setPoll(detail)
        setActivePollId(pollId)
        fetchInsights({ reset: true })
      })
      .catch(setError)
  }, [pollId]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeScope = (next) => {
    setScope(next)
    scopeRef.current.scope = next
    fetchInsights({ reset: true })
  }

  useRoomEvent(
    (event) => {
      if (event.poll_id && event.poll_id !== pollId) return
      switch (event.type) {
        case 'question_opened':
          scopeRef.current.questionId = event.question.id
          setLive((s) => s && {
            ...s,
            current_question: event.question,
            current_index: event.index,
            answered_count: 0,
            option_counts: {},
          })
          if (scopeRef.current.scope === 'question') fetchInsights({ reset: true })
          break
        case 'answer_progress':
          setLive((s) => {
            if (!s || s.current_question?.id !== event.question_id) return s
            const counts = { ...(s.option_counts || {}) }
            counts[event.option_id] = (counts[event.option_id] || 0) + 1
            return { ...s, answered_count: Math.max(s.answered_count || 0, event.answered_count), option_counts: counts }
          })
          break
        case 'insights_updated':
          if (event.version > insights.latestVersion.current) fetchInsights()
          break
        case 'poll_ended':
          setActivePollId(null)
          toast.show({
            title: 'Poll ended · first correct',
            body: <FirstCorrectToast results={event.results} />,
            tone: 'success',
            icon: <Trophy size={22} color="var(--warn)" aria-hidden="true" />,
            duration: 9000,
          })
          navigate(`/teach/polls/${pollId}`, { state: { results: event.results } })
          break
        case 'poll_cancelled':
          setActivePollId(null)
          toast.show({ title: 'Poll cancelled', body: 'No results were kept.' })
          navigate('/teach')
          break
        default:
      }
    },
    () => {
      loadLive().catch(() => {})
      fetchInsights()
    },
  )

  const act = (name, fn) => async () => {
    setBusy(name)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  const next = act('next', async () => setLive(await pollsApi.nextQuestion(pollId)))
  const end = act('end', async () => {
    const results = await pollsApi.end(pollId)
    setActivePollId(null)
    navigate(`/teach/polls/${pollId}`, { state: { results } })
  })
  const cancel = act('cancel', async () => {
    await pollsApi.cancel(pollId)
    setActivePollId(null)
    navigate('/teach')
  })

  const { seconds, label } = useCountdown(live?.deadline_at, live?.server_time)

  if (!poll || !live) return error ? <ErrorAlert error={error} /> : <LoadingBlock label="Opening live console…" />

  const q = live.current_question
  const isLast = live.current_index >= live.question_count - 1
  const onlineStudents = room.online.filter((u) => u.role === 'STUDENT').length
  const timeUp = seconds === 0

  return (
    <div className="console">
      <div className="console-top">
        <span className="live-pill" aria-live="off">
          <span className="dot" aria-hidden="true" />
          {timeUp ? 'TIME UP' : `LIVE ${label}`}
        </span>
        <h1>{poll.title}</h1>
        <span className="console-count" aria-live="polite">
          {live.answered_count ?? 0} / {Math.max(live.participant_count ?? 0, onlineStudents)} answered
        </span>
        <button type="button" className="btn btn-danger" onClick={() => setConfirmCancel(true)} disabled={!!busy}>
          <XCircle size={17} aria-hidden="true" /> Cancel poll
        </button>
        <button type="button" className="btn" onClick={next} disabled={!!busy || isLast || timeUp}>
          {busy === 'next' && <span className="spinner" aria-hidden="true" />}
          Next question <ChevronRight size={17} aria-hidden="true" />
        </button>
        <button type="button" className="btn btn-primary" onClick={end} disabled={!!busy}>
          {busy === 'end' ? <span className="spinner" aria-hidden="true" /> : <Flag size={17} aria-hidden="true" />}
          End &amp; show results
        </button>
      </div>

      <div className="console-main">
        <ErrorAlert error={error} />
        {timeUp && (
          <div className="alert alert-info" role="status">Time is up. The poll is closing and results will appear in a moment.</div>
        )}
        {q && (
          <QuestionCard
            question={q}
            index={live.current_index}
            total={live.question_count}
            deadlineAt={live.deadline_at}
            serverTime={live.server_time}
            timeLimitSeconds={poll.time_limit_seconds}
            animateKey={q.id}
          >
            <div className="options">
              {q.options.map((o) => {
                const correct = poll.questions.find((pq) => pq.id === q.id)?.options.find((po) => po.id === o.id)?.is_correct
                return (
                  <OptionRow
                    key={o.id}
                    option={o}
                    count={live.option_counts?.[o.id] ?? 0}
                    total={live.answered_count}
                    flag={correct ? 'correct' : undefined}
                  />
                )
              })}
            </div>
          </QuestionCard>
        )}
        <DrawerStrip questions={poll.questions} currentIndex={live.current_index} />
      </div>

      <div className="console-side">
        <InsightsPanel
          snapshot={insights.displayed}
          hasPending={insights.hasPending}
          questions={poll.questions}
          scope={scope}
          onScopeChange={changeScope}
        />
        <ChatPanel
          messages={room.messages}
          onSend={room.send}
          status={room.status}
          online={room.online.length}
          currentUserId={user.id}
        />
      </div>

      <ConfirmDialog
        open={confirmCancel}
        title="Cancel this poll?"
        confirmLabel="Cancel poll"
        busy={busy === 'cancel'}
        onConfirm={async () => { await cancel(); setConfirmCancel(false) }}
        onCancel={() => setConfirmCancel(false)}
      >
        Answers and AI insights for this poll are discarded and no results are kept. Chat keeps working.
      </ConfirmDialog>
    </div>
  )
}
