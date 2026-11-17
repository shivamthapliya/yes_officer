export const OPTION_LETTERS = 'ABCDEF'

/** Index-card pack colours for options A–F (always paired with the letter). */
export const OPTION_TABS = ['canary', 'sky', 'pink', 'mint', 'apricot', 'lilac']

export const letterFor = (position) => OPTION_LETTERS[position] ?? '?'
export const tabFor = (position) => OPTION_TABS[position % OPTION_TABS.length]

const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' })
const dateFmt = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
})

export const formatTime = (iso) => (iso ? timeFmt.format(new Date(iso)) : '')
export const formatDate = (iso) => (iso ? dateFmt.format(new Date(iso)) : '')
export const formatDateTime = (iso) => (iso ? dateTimeFmt.format(new Date(iso)) : '')

export const formatDuration = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (!m) return `${s} s`
  return s ? `${m} min ${s} s` : `${m} min`
}

export const pluralize = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

export const INSIGHT_LABELS = {
  COMMON_DOUBT: 'Common doubt',
  CONFUSION: 'Confusion',
  ENGAGEMENT: 'Engagement',
  MISCONCEPTION: 'Misconception',
  UNCOUNTED_RESPONSE: 'Answered in chat',
  STUDENT_QUESTION: 'Student question',
}
