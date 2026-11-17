import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { historyApi } from '../../api/services'
import { ErrorAlert, LoadingBlock } from '../../components/common'
import { OptionRow } from '../../components/QuestionCard'
import { RuledLine } from '../../components/RuledLine'
import { formatDateTime, formatTime } from '../../lib/format'
import { BackLink } from '../../components/BackLink'

export function ReviewPage() {
  const { pollId } = useParams()
  const [review, setReview] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    historyApi.review(pollId).then(setReview).catch(setError)
  }, [pollId])

  if (error) return <><BackLink to="/history">My polls</BackLink><ErrorAlert error={error} /></>
  if (!review) return <LoadingBlock />

  return (
    <div style={{ maxWidth: 900 }}>
      <BackLink to="/history">My polls</BackLink>
      <div className="page-head" style={{ marginBottom: 'var(--s-3)' }}>
        <h1>{review.title}</h1>
      </div>
      <p className="muted" style={{ marginBottom: 'var(--s-4)' }}>
        {review.room_name} · {review.teacher_name} · ended {formatDateTime(review.ended_at)}
      </p>
      <p className="review-summary num">
        <span>{review.correct_count} correct</span> · <span>{review.answered_count - review.correct_count} incorrect</span> ·{' '}
        <span>{review.question_count - review.answered_count} not answered</span>
      </p>
      <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
        {review.questions.map((q, i) => (
          <section key={q.question_id} className="index-card compact" aria-labelledby={`rv-${q.question_id}`}>
            <div className="card-head">
              <span className="call-no">Q {i + 1} OF {review.question_count}</span>
              {q.is_correct === true && <span className="stamp stamp-ok">Correct</span>}
              {q.is_correct === false && <span className="stamp stamp-closed">Incorrect</span>}
              {q.is_correct === null && <span className="stamp stamp-muted">Not answered</span>}
            </div>
            <div className="card-rule" aria-hidden="true"><i style={{ transform: 'scaleX(0)' }} /></div>
            <h2 className="card-prompt" id={`rv-${q.question_id}`}>
              {q.prompt}
            </h2>
            <div className="options" style={{ marginTop: 'var(--s-5)' }}>
              {q.options.map((o) => {
                const selected = q.selected_option_id === o.option_id
                let state
                let flag
                if (o.is_correct) {
                  state = 'correct'
                  flag = selected ? 'yours-correct' : 'correct'
                } else if (selected) {
                  state = 'wrong'
                  flag = 'wrong'
                } else {
                  state = 'faded'
                }
                return (
                  <OptionRow
                    key={o.option_id}
                    option={{ id: o.option_id, position: o.position, label: o.label }}
                    state={state}
                    flag={flag}
                  />
                )
              })}
            </div>
            <RuledLine className="muted">
              {q.selected_option_id
                ? `You answered at ${formatTime(q.answered_at)}${q.is_correct ? ' and got it right.' : '.'}`
                : 'You didn’t answer this question.'}
            </RuledLine>
          </section>
        ))}
      </div>
    </div>
  )
}
