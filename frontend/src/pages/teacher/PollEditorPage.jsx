import { ArrowDown, ArrowUp, Check, Play, Plus, Trash2, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
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
  const problems = []
  if (!local.prompt.trim()) problems.push('Write the question')
  if (filled.length < MIN_OPTIONS) problems.push(`Add at least ${MIN_OPTIONS} options`)
  if (local.options.filter((o) => o.is_correct).length !== 1) problems.push('Mark the correct answer')
  return problems
}

function QuestionEditor({ question, index, total, onSave, onDelete, onMove, onDirtyChange, onDiscardNew }) {
  const [local, setLocal] = useState(() => toLocal(question))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const baseline = useRef(toLocal(question))
  const dirty = !question || !same(local, baseline.current)
  const problems = readiness(local)

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
    <section className="index-card q-editor" aria-label={`Question ${index + 1}`}>
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
      <div className="card-rule" aria-hidden="true"><i /></div>
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
          <div className="opt-edit" key={i} style={{ '--tab': `var(--tab-${tabFor(i)})` }}>
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
                className="btn btn-ghost btn-icon btn-sm"
                aria-label={`Remove option ${letterFor(i)}`}
                disabled={local.options.length <= MIN_OPTIONS}
                onClick={() => setLocal({ ...local, options: local.options.filter((_, j) => j !== i) })}
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
          onClick={() => setLocal({ ...local, options: [...local.options, { label: '', is_correct: false }] })}
        >
          <Plus size={15} aria-hidden="true" /> Add option
        </button>
        <span style={{ flex: 1 }} />
        {problems.length > 0 ? (
          <span className="save-state">{problems.join(' · ')}</span>
        ) : (
          <span className="save-state">{dirty ? 'Unsaved changes' : 'Saved'}</span>
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

  const saveMeta = async (patch) => {
    const next = { ...meta, ...patch }
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
      apply(await pollsApi.removeQuestion(questionId))
    } catch (err) {
      setError(err)
    }
  }

  const move = (index, delta) => async () => {
    const ids = poll.questions.map((q) => q.id)
    const [item] = ids.splice(index, 1)
    ids.splice(index + delta, 0, item)
    try {
      apply(await pollsApi.reorder(pollId, ids))
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
        <label className="field">
          <span>Time limit: <span className="num">{formatDuration(meta.time_limit_seconds)}</span></span>
          <span className="time-limit">
            <input
              type="range"
              min={10}
              max={300}
              step={10}
              value={meta.time_limit_seconds}
              aria-describedby="time-help"
              onChange={(e) => setMeta({ ...meta, time_limit_seconds: Number(e.target.value) })}
              onPointerUp={() => saveMeta({})}
              onKeyUp={() => saveMeta({})}
            />
          </span>
          <small id="time-help">For the whole poll, up to 5 minutes. {metaState === 'saving' ? 'Saving…' : metaState === 'saved' ? 'Saved.' : ''}</small>
        </label>
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
