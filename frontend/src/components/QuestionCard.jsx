import { Check, X } from 'lucide-react'

import { useCountdown } from '../hooks/useCountdown'
import { letterFor, tabFor } from '../lib/format'

/**
 * The signature index card: call number, a red header rule that drains with the
 * poll's remaining time, the prompt, and option rows wearing card-pack tabs.
 */
export function QuestionCard({
  question,
  index,
  total,
  deadlineAt,
  serverTime,
  timeLimitSeconds,
  headRight,
  children,
  animateKey,
}) {
  const { remainingMs, label } = useCountdown(deadlineAt, serverTime)
  const fraction = remainingMs == null || !timeLimitSeconds ? 1 : Math.min(1, remainingMs / (timeLimitSeconds * 1000))

  return (
    <section className="index-card card-enter" key={animateKey} aria-labelledby={`q-${question.id}`}>
      <div className="card-head">
        <span className="call-no">
          Q {index + 1} OF {total}
        </span>
        {headRight ?? (deadlineAt && <span className="call-no" aria-hidden="true">{label} LEFT</span>)}
      </div>
      <div className="card-rule" aria-hidden="true">
        <i style={{ transform: `scaleX(${fraction})` }} />
      </div>
      <h2 className="card-prompt" id={`q-${question.id}`}>
        {question.prompt}
      </h2>
      {children}
    </section>
  )
}

export function OptionRow({ option, as = 'div', state, count, total, onClick, disabled, flag, display = 'count' }) {
  const Tag = as
  const share = total ? count / total : 0
  const percent = Math.round(share * 100)
  return (
    <Tag
      className="opt"
      data-state={state}
      style={{ '--tab': `var(--tab-${tabFor(option.position)})` }}
      onClick={onClick}
      disabled={as === 'button' ? disabled : undefined}
      type={as === 'button' ? 'button' : undefined}
      aria-pressed={as === 'button' ? state === 'chosen' || state === 'pending' : undefined}
    >
      <span className="opt-tab" aria-hidden="true">
        {letterFor(option.position)}
      </span>
      <span className="opt-letter" aria-hidden="true">
        {letterFor(option.position)}
      </span>
      <span className="opt-label">
        <span className="sr-only">Option {letterFor(option.position)}: </span>
        {option.label}
      </span>
      {flag === 'correct' && (
        <span className="opt-flag ok">
          <Check size={16} aria-hidden="true" /> Correct
        </span>
      )}
      {flag === 'wrong' && (
        <span className="opt-flag bad">
          <X size={16} aria-hidden="true" /> Your answer
        </span>
      )}
      {flag === 'yours-correct' && (
        <span className="opt-flag ok">
          <Check size={16} aria-hidden="true" /> Your answer · correct
        </span>
      )}
      {count != null && display === 'percent' && (
        <span className="opt-count" aria-label={`${percent}% of answers (${count})`}>
          {percent}
          <small aria-hidden="true">%</small>
        </span>
      )}
      {count != null && display !== 'percent' && (
        <span className="opt-count" aria-label={`${count} answers`}>
          {count}
        </span>
      )}
      {count != null && (
        <span className="opt-meter" aria-hidden="true">
          <i style={{ transform: `scaleX(${share})` }} />
        </span>
      )}
    </Tag>
  )
}

export function DrawerStrip({ questions, currentIndex, label = 'Questions in this poll' }) {
  return (
    <ol className="drawer" aria-label={label} style={{ listStyle: 'none', margin: 0 }}>
      {questions.map((q, i) => {
        const state = i === currentIndex ? 'open' : i < currentIndex ? 'done' : 'queued'
        return (
          <li key={q.id} className="drawer-card" data-state={state} aria-current={state === 'open' ? 'step' : undefined}>
            <b>Q{i + 1}</b>
            <span>{q.prompt}</span>
          </li>
        )
      })}
    </ol>
  )
}

