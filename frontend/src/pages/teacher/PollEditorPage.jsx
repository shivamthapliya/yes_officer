import { ArrowDown, ArrowUp, Check, Minus, Play, Plus, Trash2, X } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { useNavigate, useParams } from 'react-router-dom'

import { pollsApi } from '../../api/services'
import { ConfirmDialog, ErrorAlert, LoadingBlock } from '../../components/common'
import { formatDuration, letterFor, tabFor } from '../../lib/format'
import { BackLink } from '../../components/BackLink'

const MAX_OPTIONS = 6
const MIN_OPTIONS = 2

const blankOptions = () => [{ label: '', is_correct: false }, { label: '', is_correct: false }]
const toLocal = (q) => ({
  prompt: q?.prompt ?? '',
  options: q ? q.options.map((o) => ({ label: o.label, is_correct: o.is_correct })) : blankOptions(),
})
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)

function readiness(local) {
  const filled = local.options.filter((o) => o.label.trim())
  return [
    { label: 'Write the question', done: Boolean(local.prompt.trim()) },
    { label: `Add at least ${MIN_OPTIONS} options`, done: filled.length >= MIN_OPTIONS },
    { label: 'Mark the correct answer', done: local.options.filter((o) => o.is_correct).length === 1 },
  ]
}

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

function QuestionEditor({ question, index, total, onSave, onDelete, onMove, onDirtyChange, onDiscardNew }) {
  const [local, setLocal] = useState(() => toLocal(question))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const baseline = useRef(toLocal(question))
  const dirty = !question || !same(local, baseline.current)
  const checks = readiness(local)
  const doneCount = checks.filter((c) => c.done).length
  const ready = doneCount === checks.length
  const [newOption, setNewOption] = useState(null)
  const [leaving, setLeaving] = useState(null)

  // Fade and slide the row out, fold its height away, then drop it from the list.
  const removeOption = (i, rowEl) => {
    if (leaving !== null) return
    const drop = () => {
      setLocal((s) => ({ ...s, options: s.options.filter((_, j) => j !== i) }))
      setLeaving(null)
    }
    if (prefersReducedMotion() || !rowEl) return drop()
    setLeaving(i)
    const h = rowEl.getBoundingClientRect().height
    rowEl.style.overflow = 'hidden'
    rowEl
      .animate(
        [
          { opacity: 1, transform: 'none', filter: 'none', height: `${h}px` },
          { opacity: 0, transform: 'translateX(24px) scale(0.98)', filter: 'blur(2px)', height: `${h}px`, offset: 0.55 },
          { opacity: 0, transform: 'translateX(24px) scale(0.98)', filter: 'blur(2px)', height: '0px', paddingTop: '0px', paddingBottom: '0px' },
        ],
        { duration: 340, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'forwards' },
      )
      .finished.then(() => {
        // Remove the option from the DOM first, then clear the animation in the same frame.
        // Rows are keyed by index, so this element may now hold the next option.
        flushSync(drop)
        rowEl.getAnimations().forEach((a) => a.cancel())
        rowEl.style.overflow = ''
      })
  }

  useEffect(() => {
    onDirtyChange(dirty)
  }, [dirty, onDirtyChange])
  useEffect(() => () => onDirtyChange(false), [onDirtyChange])

  const setOption = (i, patch) =>
    setLocal((s) => ({
      ...s,
      options: s.options.map((o, j) => {
        if (patch.is_correct) return j === i ? { ...o, is_correct: !o.is_correct } : { ...o, is_correct: false }
        return j === i ? { ...o, ...patch } : o
      }),
    }))

  const save = async () => {
    setBusy(true)
    setError(null)
    const body = {
      prompt: local.prompt,
      options: local.options.filter((o) => o.label.trim()).map((o) => ({ label: o.label.trim(), is_correct: o.is_correct })),
    }
    try {
      const saved = await onSave(question?.id, body)
      if (saved) {
        baseline.current = toLocal(saved)
        setLocal(toLocal(saved))
      }
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      className={`index-card q-editor${question ? '' : ' card-enter'}`}
      data-qid={question?.id}
      data-ready={ready || undefined}
      aria-label={`Question ${index + 1}`}
    >
      <div className="card-head">
        <span className="call-no">Q {index + 1} OF {total}</span>
        <span style={{ display: 'flex', gap: 4 }}>
          {question && (
            <>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => onMove(-1)} disabled={index === 0} aria-label="Move question up">
                <ArrowUp size={16} aria-hidden="true" />
              </button>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => onMove(1)} disabled={index === total - 1} aria-label="Move question down">
                <ArrowDown size={16} aria-hidden="true" />
              </button>
            </>
          )}
          <button
            type="button"
            className="btn btn-ghost btn-icon btn-sm"
            onClick={() => (question ? onDelete(question.id) : onDiscardNew())}
            aria-label={question ? 'Delete question' : 'Discard new question'}
          >
            <Trash2 size={16} aria-hidden="true" />
          </button>
        </span>
      </div>
      <div className="card-rule" aria-hidden="true">
        <i style={{ transform: `scaleX(${doneCount / checks.length})` }} />
      </div>
      <label className="sr-only" htmlFor={`prompt-${index}`}>Question text</label>
      <textarea
        id={`prompt-${index}`}
        className="textarea"
        placeholder="Type the question…"
        maxLength={1000}
        value={local.prompt}
        onChange={(e) => setLocal({ ...local, prompt: e.target.value })}
      />
      <div style={{ marginTop: 'var(--s-4)' }} role="group" aria-label="Options">
        {local.options.map((o, i) => (
          <div
            className={`opt-edit${newOption === i ? ' opt-new' : ''}`}
            key={i}
            style={{ '--tab': `var(--tab-${tabFor(i)})` }}
            onAnimationEnd={(e) => e.target === e.currentTarget && newOption === i && setNewOption(null)}
          >
            <span className="tab-dot" aria-hidden="true" />
            <span className="opt-letter" aria-hidden="true">{letterFor(i)}</span>
            <input
              className="input"
              aria-label={`Option ${letterFor(i)}`}
              placeholder={`Option ${letterFor(i)}`}
              maxLength={500}
              value={o.label}
              onChange={(e) => setOption(i, { label: e.target.value })}
            />
            <span style={{ display: 'flex', gap: 4 }}>
              <button type="button" className="correct-toggle" aria-pressed={o.is_correct} onClick={() => setOption(i, { is_correct: true })}>
                <Check size={15} aria-hidden="true" /> {o.is_correct ? 'Correct' : 'Mark correct'}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-icon btn-sm opt-remove"
                aria-label={`Remove option ${letterFor(i)}`}
                disabled={local.options.length <= MIN_OPTIONS || leaving !== null}
                onClick={(e) => removeOption(i, e.currentTarget.closest('.opt-edit'))}
              >
                <X size={16} aria-hidden="true" />
              </button>
            </span>
          </div>
        ))}
      </div>
      <div className="q-actions">
        <button
          type="button"
          className="btn btn-sm"
          disabled={local.options.length >= MAX_OPTIONS}
          onClick={() => {
            setNewOption(local.options.length)
            setLocal({ ...local, options: [...local.options, { label: '', is_correct: false }] })
          }}
        >
          <Plus size={15} aria-hidden="true" /> Add option
        </button>
        <span style={{ flex: 1 }} />
        {ready ? (
          <span key={dirty ? 'dirty' : 'saved'} className="save-state save-state-in">{dirty ? 'Unsaved changes' : 'Saved'}</span>
        ) : (
          <span className="save-state checklist">
            {checks.map((c) => (
              <span key={c.label} className="check-item" data-done={c.done || undefined}>
                {c.label}
                {c.done && <span className="sr-only"> (done)</span>}
              </span>
            ))}
          </span>
        )}
        <button type="button" className="btn btn-primary btn-sm" onClick={save} disabled={busy || !dirty || !local.prompt.trim()}>
          {busy && <span className="spinner" aria-hidden="true" />}
          {question ? 'Save question' : 'Add to poll'}
        </button>
      </div>
      {error && <div style={{ marginTop: 'var(--s-3)' }}><ErrorAlert error={error} /></div>}
    </section>
  )
}

const TIME_MIN = 10
const TIME_MAX = 300
const TIME_STEP = 10
const TIME_PRESETS = [
  { seconds: 30, label: '30s' },
  { seconds: 60, label: '1m' },
  { seconds: 120, label: '2m' },
  { seconds: 180, label: '3m' },
  { seconds: 300, label: '5m' },
]

function TimeLimitPicker({ value, onChange }) {
  const set = (v) => onChange(Math.min(TIME_MAX, Math.max(TIME_MIN, v)))
  const m = Math.floor(value / 60)
  const s = String(value % 60).padStart(2, '0')

  return (
    <div className="time-picker" role="group" aria-labelledby="time-label" aria-describedby="time-help">
      <div className="time-stepper">
        <button type="button" className="time-step" aria-label="10 seconds less" disabled={value <= TIME_MIN} onClick={() => set(value - TIME_STEP)}>
          <Minus size={16} aria-hidden="true" />
        </button>
        <output className="time-readout" aria-live="polite" aria-label={formatDuration(value)}>
          <span key={value} className="time-digits">{m}:{s}</span>
        </output>
        <button type="button" className="time-step" aria-label="10 seconds more" disabled={value >= TIME_MAX} onClick={() => set(value + TIME_STEP)}>
          <Plus size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="time-presets">
        {TIME_PRESETS.map((p) => (
          <button key={p.seconds} type="button" aria-pressed={value === p.seconds} aria-label={formatDuration(p.seconds)} onClick={() => set(p.seconds)}>
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PollEditorPage() {
  const { pollId } = useParams()
  const navigate = useNavigate()
  const [poll, setPoll] = useState(null)
  const [error, setError] = useState(null)
  const [meta, setMeta] = useState({ title: '', time_limit_seconds: 120 })
  const [metaState, setMetaState] = useState('saved')
  const [drafts, setDrafts] = useState([])
  const [dirtyMap, setDirtyMap] = useState({})
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [starting, setStarting] = useState(false)
  const draftSeq = useRef(0)

  // FLIP: capture card positions before a reorder or delete, then slide them from there.
  const flipFrom = useRef(null)
  const snapshotCards = () => {
    flipFrom.current = new Map(
      [...document.querySelectorAll('.editor [data-qid]')].map((el) => [el.dataset.qid, el.getBoundingClientRect().top]),
    )
  }
  useLayoutEffect(() => {
    const from = flipFrom.current
    if (!from) return
    flipFrom.current = null
    if (prefersReducedMotion()) return
    document.querySelectorAll('.editor [data-qid]').forEach((el) => {
      const before = from.get(el.dataset.qid)
      if (before === undefined) return
      const dy = before - el.getBoundingClientRect().top
      if (Math.abs(dy) < 1) return
      el.animate([{ transform: `translateY(${dy}px)` }, { transform: 'none' }], {
        duration: 480,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      })
    })
  }, [poll])

  const apply = useCallback((detail) => {
    setPoll(detail)
    return detail
  }, [])

  useEffect(() => {
    pollsApi
      .detail(pollId)
      .then((detail) => {
        if (detail.status === 'ACTIVE') navigate(`/teach/polls/${pollId}/live`, { replace: true })
        else if (detail.status !== 'DRAFT') navigate(`/teach/polls/${pollId}`, { replace: true })
        apply(detail)
        setMeta({ title: detail.title, time_limit_seconds: detail.time_limit_seconds })
        if (detail.questions.length === 0) setDrafts([`new-${(draftSeq.current += 1)}`])
      })
      .catch(setError)
  }, [pollId, navigate, apply])

  const metaRef = useRef(meta)
  metaRef.current = meta
  const timeSaveTimer = useRef(null)
  useEffect(() => () => clearTimeout(timeSaveTimer.current), [])

  const saveMeta = async (patch) => {
    const next = { ...metaRef.current, ...patch }
    setMeta(next)
    if (!next.title.trim()) return
    setMetaState('saving')
    try {
      apply(await pollsApi.update(pollId, { title: next.title, time_limit_seconds: next.time_limit_seconds }))
      setMetaState('saved')
    } catch (err) {
      setError(err)
      setMetaState('error')
    }
  }

  const scheduleTimeSave = (seconds) => {
    clearTimeout(timeSaveTimer.current)
    timeSaveTimer.current = setTimeout(() => saveMeta({ time_limit_seconds: seconds }), 450)
  }

  const markDirty = useCallback((key) => (isDirty) => setDirtyMap((m) => (m[key] === isDirty ? m : { ...m, [key]: isDirty })), [])
  const dirtyHandlers = useRef({})
  const dirtyFor = (key) => (dirtyHandlers.current[key] ??= markDirty(key))

  const saveQuestion = (draftKey) => async (questionId, body) => {
    if (questionId) {
      const detail = apply(await pollsApi.updateQuestion(questionId, body))
      return detail.questions.find((q) => q.id === questionId)
    }
    apply(await pollsApi.addQuestion(pollId, body))
    setDrafts((d) => d.filter((k) => k !== draftKey))
    return null
  }

  const deleteQuestion = async (questionId) => {
    try {
      const detail = await pollsApi.removeQuestion(questionId)
      snapshotCards()
      apply(detail)
    } catch (err) {
      setError(err)
    }
  }

  const move = (index, delta) => async () => {
    const ids = poll.questions.map((q) => q.id)
    const [item] = ids.splice(index, 1)
    ids.splice(index + delta, 0, item)
    try {
      const detail = await pollsApi.reorder(pollId, ids)
      snapshotCards()
      apply(detail)
    } catch (err) {
      setError(err)
    }
  }

  const start = async () => {
    setStarting(true)
    setError(null)
    try {
      await pollsApi.start(pollId)
      navigate(`/teach/polls/${pollId}/live`)
    } catch (err) {
      setError(err)
      setStarting(false)
    }
  }

  const remove = async () => {
    try {
      await pollsApi.remove(pollId)
      navigate('/teach')
    } catch (err) {
      setError(err)
      setConfirmDelete(false)
    }
  }

  if (!poll) return error ? <ErrorAlert error={error} /> : <LoadingBlock />

  const unsaved = Object.values(dirtyMap).some(Boolean)
  const total = poll.questions.length + drafts.length

  return (
    <div className="editor">
      <div>
        <BackLink to="/teach">My room</BackLink>
        <div className="page-head" style={{ marginBottom: 0 }}>
          <h1>Edit poll</h1>
          <span className="spacer" />
          <button type="button" className="btn btn-danger" onClick={() => setConfirmDelete(true)}>
            <Trash2 size={16} aria-hidden="true" /> Delete draft
          </button>
          <button type="button" className="btn btn-primary" onClick={start} disabled={starting || unsaved || poll.questions.length === 0}>
            {starting ? <span className="spinner" aria-hidden="true" /> : <Play size={17} aria-hidden="true" />}
            Start poll
          </button>
        </div>
        {unsaved && <p className="save-state" style={{ marginTop: 8 }}>Save or discard your question edits before starting.</p>}
      </div>

      <ErrorAlert error={error} />

      <div className="editor-meta">
        <label className="field">
          <span>Poll title</span>
          <input
            className="input"
            value={meta.title}
            maxLength={200}
            onChange={(e) => setMeta({ ...meta, title: e.target.value })}
            onBlur={() => meta.title !== poll.title && saveMeta({})}
          />
        </label>
        <div className="field">
          <span id="time-label">Time limit</span>
          <TimeLimitPicker
            value={meta.time_limit_seconds}
            onChange={(v) => {
              setMeta((m) => ({ ...m, time_limit_seconds: v }))
              scheduleTimeSave(v)
            }}
          />
          <small id="time-help">For the whole poll, up to 5 minutes. {metaState === 'saving' ? 'Saving…' : metaState === 'saved' ? 'Saved.' : ''}</small>
        </div>
      </div>

      {poll.questions.map((q, i) => (
        <QuestionEditor
          key={q.id}
          question={q}
          index={i}
          total={total}
          onSave={saveQuestion(null)}
          onDelete={deleteQuestion}
          onMove={(delta) => move(i, delta)()}
          onDirtyChange={dirtyFor(q.id)}
        />
      ))}
      {drafts.map((key, i) => (
        <QuestionEditor
          key={key}
          question={null}
          index={poll.questions.length + i}
          total={total}
          onSave={saveQuestion(key)}
          onDiscardNew={() => setDrafts((d) => d.filter((k) => k !== key))}
          onMove={() => {}}
          onDirtyChange={dirtyFor(key)}
        />
      ))}
      <button type="button" className="btn" style={{ justifySelf: 'start' }} onClick={() => setDrafts((d) => [...d, `new-${(draftSeq.current += 1)}`])}>
        <Plus size={17} aria-hidden="true" /> Add question
      </button>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this draft?"
        confirmLabel="Delete draft"
        onConfirm={remove}
        onCancel={() => setConfirmDelete(false)}
      >
        “{poll.title}” and its {poll.questions.length} questions will be removed. This can’t be undone.
      </ConfirmDialog>
    </div>
  )
}
