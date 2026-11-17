import { Coffee, DoorOpen, Trophy } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { answersApi, roomsApi } from '../../api/services'
import { ChatPanel } from '../../components/ChatPanel'
import { EmptyState, ErrorAlert, LoadingBlock } from '../../components/common'
import { OptionRow, QuestionCard } from '../../components/QuestionCard'
import { FirstCorrectToast, ResultsBoard } from '../../components/ResultsBoard'
import { useAuth } from '../../context/AuthContext'
import { RoomLiveProvider, useRoomEvent, useRoomLive } from '../../context/RoomLiveContext'
import { useToast } from '../../context/ToastContext'
import { useCountdown } from '../../hooks/useCountdown'
import { formatTime } from '../../lib/format'

const REJECTIONS = {
  ANSWER_POLL_CLOSED: 'This poll has closed.',
  ANSWER_EXPIRED: 'Time ran out before your answer arrived.',
  ANSWER_NOT_CURRENT: 'Your teacher moved on to the next question.',
}

function LiveRoom({ room }) {
  const { user } = useAuth()
  const toast = useToast()
  const live = useRoomLive()
  const [poll, setPoll] = useState(undefined) // undefined = loading, null = no live poll
  const [answers, setAnswers] = useState({}) // question_id -> { status, optionId, receivedAt, error }
  const [results, setResults] = useState(null)
  const [notice, setNotice] = useState(null)
  const [tab, setTab] = useState('question')
  const [unread, setUnread] = useState(0)
  const lastSeen = useRef(0)

  const loadPoll = useCallback(async () => {
    const state = await roomsApi.activePoll(room.id)
    setPoll(state)
    if (state?.current_question && state.my_answer_option_id) {
      setAnswers((a) => ({
        ...a,
        [state.current_question.id]: a[state.current_question.id] ?? { status: 'accepted', optionId: state.my_answer_option_id },
      }))
    }
  }, [room.id])

  useEffect(() => {
    loadPoll().catch(() => setPoll(null))
  }, [loadPoll])

  useEffect(() => {
    if (tab === 'chat') {
      lastSeen.current = live.messages.length
      setUnread(0)
    } else {
      setUnread(Math.max(0, live.messages.length - lastSeen.current))
    }
  }, [live.messages.length, tab])

  useRoomEvent(
    (event) => {
      switch (event.type) {
        case 'poll_started':
          setResults(null)
          setNotice(null)
          setAnswers({})
          setTab('question')
          break
        case 'question_opened':
          setPoll((p) =>
            p && p.poll_id === event.poll_id
              ? { ...p, current_question: event.question, current_index: event.index, deadline_at: event.deadline_at }
              : p,
          )
          loadPoll().catch(() => {})
          break
        case 'poll_ended':
          setPoll(null)
          setResults(event.results)
          setTab('question')
          toast.show({
            title: 'Results are in · first correct',
            body: <FirstCorrectToast results={event.results} />,
            tone: 'success',
            icon: <Trophy size={22} color="var(--warn)" aria-hidden="true" />,
            duration: 9000,
          })
          break
        case 'poll_cancelled':
          setPoll(null)
          setNotice('Your teacher cancelled the poll. No answers were kept.')
          break
        default:
      }
    },
    () => loadPoll().catch(() => {}),
  )

  const submit = async (question, option) => {
    setAnswers((a) => ({ ...a, [question.id]: { status: 'sending', optionId: option.id } }))
    try {
      const receipt = await answersApi.submit(poll.poll_id, question.id, option.id)
      setAnswers((a) => ({
        ...a,
        [question.id]: { status: 'accepted', optionId: receipt.option_id, receivedAt: receipt.received_at, duplicate: receipt.status === 'duplicate' },
      }))
    } catch (err) {
      setAnswers((a) => ({ ...a, [question.id]: { status: 'error', error: REJECTIONS[err.code] || err.message } }))
    }
  }

  const { seconds, label } = useCountdown(poll?.deadline_at, poll?.server_time)
  const myAnswers = Object.fromEntries(
    Object.entries(answers).filter(([, a]) => a.status === 'accepted').map(([q, a]) => [q, a.optionId]),
  )

  const q = poll?.current_question
  const mine = q ? answers[q.id] : null
  const locked = mine?.status === 'accepted' || mine?.status === 'sending' || seconds === 0

  return (
    <div>
      <div className="page-head">
        <h1>{room.name}</h1>
        {!room.name.includes(room.teacher_name) && <span className="muted">{room.teacher_name}</span>}
        <span className="spacer" />
        {poll && <span className="live-pill"><span className="dot" aria-hidden="true" />{seconds === 0 ? 'TIME UP' : `LIVE ${label}`}</span>}
      </div>

      <div className="room-tabs">
        <div className="segmented" role="tablist" aria-label="Room view">
          <button type="button" role="tab" aria-selected={tab === 'question'} aria-pressed={tab === 'question'} onClick={() => setTab('question')}>
            Poll
          </button>
          <button type="button" role="tab" aria-selected={tab === 'chat'} aria-pressed={tab === 'chat'} onClick={() => setTab('chat')}>
            Chat{unread > 0 && ` (${unread})`}
          </button>
        </div>
      </div>

      <div className="student-room" data-tab={tab}>
        <div className="question-col">
          {notice && <div className="alert alert-info" role="status" style={{ marginBottom: 'var(--s-4)' }}>{notice}</div>}
          {poll === undefined ? (
            <LoadingBlock />
          ) : q ? (
            <QuestionCard
              question={q}
              index={poll.current_index}
              total={poll.question_count}
              deadlineAt={poll.deadline_at}
              serverTime={poll.server_time}
              timeLimitSeconds={poll.deadline_at && poll.started_at ? (new Date(poll.deadline_at) - new Date(poll.started_at)) / 1000 : null}
              animateKey={q.id}
            >
              <div className="options" role="group" aria-label="Choose one answer">
                {q.options.map((o) => {
                  let state
                  if (mine?.optionId === o.id) state = mine.status === 'accepted' ? 'chosen' : mine.status === 'sending' ? 'pending' : undefined
                  else if (mine?.status === 'accepted') state = 'faded'
                  return (
                    <OptionRow key={o.id} as="button" option={o} state={state} disabled={locked} onClick={() => submit(q, o)} />
                  )
                })}
              </div>
              <div className="answer-foot" aria-live="assertive">
                {mine?.status === 'accepted' && (
                  <span className="stamp stamp-ok stamp-in">
                    {mine.duplicate ? 'Already answered' : 'Answer accepted'}
                    {mine.receivedAt && ` · ${formatTime(mine.receivedAt)}`}
                  </span>
                )}
                {mine?.status === 'sending' && <span className="stamp stamp-pending">Sending…</span>}
                {mine?.status === 'error' && <span className="stamp stamp-closed">{mine.error}</span>}
                {!mine && seconds === 0 && <span className="stamp stamp-closed">Time’s up</span>}
                {!mine && seconds !== 0 && <span className="muted">Tap an answer. Your first answer counts.</span>}
              </div>
            </QuestionCard>
          ) : results ? (
            <>
              <div className="page-head" style={{ marginBottom: 'var(--s-4)' }}>
                <h2 style={{ fontSize: 'var(--t-xl)' }}>Results: {results.title}</h2>
                <span className="spacer" />
                <Link className="btn btn-sm" to={`/history/${results.poll_id}`}>Review my answers</Link>
              </div>
              <ResultsBoard results={results} myAnswers={myAnswers} />
            </>
          ) : (
            <section className="index-card compact waiting-card">
              <Coffee size={36} strokeWidth={1.5} aria-hidden="true" />
              <h2 className="card-prompt" style={{ marginTop: 'var(--s-3)' }}>No poll running right now</h2>
              <p className="muted" style={{ marginTop: 'var(--s-2)' }}>
                Stay here. When your teacher starts a poll, the first question appears on this card.
              </p>
            </section>
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
    </div>
  )
}

export function StudentRoomPage() {
  const { roomId } = useParams()
  const [room, setRoom] = useState(null)
  const [error, setError] = useState(null)
  const [joining, setJoining] = useState(false)

  const load = useCallback(() => roomsApi.detail(roomId).then(setRoom).catch(setError), [roomId])
  useEffect(() => {
    load()
  }, [load])

  if (error) return <ErrorAlert error={error} />
  if (!room) return <LoadingBlock />

  if (!room.is_joined) {
    return (
      <div className="list-card" style={{ maxWidth: 640 }}>
        <EmptyState
          icon={DoorOpen}
          title={`Join ${room.name}?`}
          action={
            <button
              type="button"
              className="btn btn-primary"
              disabled={joining}
              onClick={async () => {
                setJoining(true)
                try {
                  await roomsApi.join(roomId)
                  await load()
                } catch (err) {
                  setError(err)
                }
              }}
            >
              Join room
            </button>
          }
        >
          {room.teacher_name}’s room. Join to chat with the class and answer live polls.
        </EmptyState>
      </div>
    )
  }

  return (
    <RoomLiveProvider roomId={room.id}>
      <LiveRoom room={room} />
    </RoomLiveProvider>
  )
}
