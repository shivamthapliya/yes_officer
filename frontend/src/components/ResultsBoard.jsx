import { Check, Trophy, Users } from 'lucide-react'

import { formatTime, pluralize } from '../lib/format'
import { OptionRow } from './QuestionCard'
import { RuledLine } from './RuledLine'

/** Verified per-question results: distribution, correct option, first correct student. */
export function ResultsBoard({ results, myAnswers = null }) {
  return (
    <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
      {results.questions.map((q, i) => (
        <section key={q.question_id} className="index-card compact" aria-labelledby={`r-${q.question_id}`}>
          <div className="card-head">
            <span className="call-no">
              Q {i + 1} OF {results.questions.length}
            </span>
            <span className="verified-label">Verified answers</span>
          </div>
          <div className="card-rule" aria-hidden="true">
            <i style={{ transform: 'scaleX(0)' }} />
          </div>
          <h2 className="card-prompt" id={`r-${q.question_id}`}>
            {q.prompt}
          </h2>
          <p className="meta" style={{ marginTop: 'var(--s-3)', display: 'flex', gap: 'var(--s-4)', flexWrap: 'wrap' }}>
            <span>
              <Users size={13} aria-hidden="true" style={{ verticalAlign: '-2px' }} /> {q.answered_count} of{' '}
              {pluralize(q.participant_count, 'participant')} answered
            </span>
            <span className="correct-share">
              <Check size={13} aria-hidden="true" style={{ verticalAlign: '-2px' }} />{' '}
              {q.answered_count ? Math.round((100 * q.correct_count) / q.answered_count) : 0}% got it right
            </span>
          </p>
          <div className="options" style={{ marginTop: 'var(--s-5)' }}>
            {q.options.map((o) => {
              const mine = myAnswers?.[q.question_id] === o.option_id
              let state
              let flag
              if (o.is_correct) {
                state = 'correct'
                flag = 'correct'
              } else if (mine) {
                state = 'wrong'
                flag = 'wrong'
              }
              return (
                <OptionRow
                  key={o.option_id}
                  option={{ id: o.option_id, position: o.position, label: `${o.label}` }}
                  state={state}
                  flag={flag}
                  count={o.count}
                  total={q.answered_count}
                  display="percent"
                />
              )
            })}
          </div>
          <RuledLine style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            {q.first_correct_student ? (
              <>
                <Trophy size={18} aria-hidden="true" color="var(--warn)" style={{ alignSelf: 'center' }} />
                <span>
                  First correct: <strong>{q.first_correct_student.full_name}</strong>{' '}
                  <span className="meta">at {formatTime(q.first_correct_student.received_at)}</span>
                </span>
              </>
            ) : (
              <span className="muted">No one picked the correct answer.</span>
            )}
          </RuledLine>
        </section>
      ))}
    </div>
  )
}

/** Toast body announcing the first correct student per question (D5). */
export function FirstCorrectToast({ results }) {
  const winners = results.questions.filter((q) => q.first_correct_student)
  if (!winners.length) return <span>No one got a correct answer first this time.</span>
  return (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      {results.questions.map((q, i) =>
        q.first_correct_student ? (
          <li key={q.question_id}>
            Q{i + 1}: <strong>{q.first_correct_student.full_name}</strong>
          </li>
        ) : null,
      )}
    </ul>
  )
}
