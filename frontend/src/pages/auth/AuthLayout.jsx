import { useEffect, useRef, useState } from 'react'

import { BrandMark } from '../../components/BrandMark'
import { CatalogScene } from '../../components/CatalogScene'
import { OptionRow } from '../../components/QuestionCard'
import { SiteFooter } from '../../components/SiteFooter'

const SAMPLES = [
  {
    prompt: 'Which organelle produces most of a cell’s ATP?',
    options: ['Nucleus', 'Mitochondrion', 'Ribosome'],
    pick: 1,
  },
  {
    prompt: 'Which planet has the shortest year?',
    options: ['Mercury', 'Venus', 'Mars'],
    pick: 0,
  },
  {
    prompt: 'Which gas do plants take in for photosynthesis?',
    options: ['Oxygen', 'Carbon dioxide', 'Nitrogen'],
    pick: 1,
  },
]

const LIMIT = 45
const pad = (n) => String(n).padStart(2, '0')
const clock = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

/** The sample card runs a tiny poll on a loop: countdown, a tap, the stamp, the next card. */
function LiveSampleCard() {
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [index, setIndex] = useState(0)
  const [left, setLeft] = useState(41)
  const [phase, setPhase] = useState(reduced ? 'stamped' : 'asking') // asking → pending → stamped → leaving
  const [stampTime, setStampTime] = useState(() => clock(new Date()))

  useEffect(() => {
    if (reduced) return undefined
    const timers = []
    const at = (ms, fn) => timers.push(setTimeout(fn, ms))
    const startLeft = 41 - index * 7
    setLeft(startLeft)
    setPhase('asking')
    for (let s = 1; s <= 5; s += 1) at(s * 1000, () => setLeft(startLeft - s))
    at(1700, () => setPhase('pending'))
    at(2300, () => {
      setStampTime(clock(new Date()))
      setPhase('stamped')
    })
    at(5600, () => setPhase('leaving'))
    at(6100, () => setIndex((i) => (i + 1) % SAMPLES.length))
    return () => timers.forEach(clearTimeout)
  }, [index, reduced])

  const sample = SAMPLES[index]
  const stateFor = (i) => {
    if (i !== sample.pick) return phase === 'stamped' || phase === 'leaving' ? 'faded' : undefined
    if (phase === 'pending') return 'pending'
    if (phase === 'stamped' || phase === 'leaving') return 'chosen'
    return undefined
  }

  return (
    <section key={index} className={`index-card compact auth-card ${phase === 'leaving' ? 'auth-card-leave' : 'card-enter'}`}>
      <div className="card-head">
        <span className="call-no">Q {index + 2} OF 5</span>
        <span className="call-no">00:{pad(left)} LEFT</span>
      </div>
      <div className="card-rule">
        <i style={{ transform: `scaleX(${left / LIMIT})`, transition: 'transform 1s linear' }} />
      </div>
      <p className="card-prompt">{sample.prompt}</p>
      <div className="options" style={{ gridTemplateColumns: '1fr' }}>
        {sample.options.map((label, i) => (
          <OptionRow key={label} option={{ id: label, position: i, label }} state={stateFor(i)} />
        ))}
      </div>
      {(phase === 'stamped' || phase === 'leaving') && (
        <span className="stamp stamp-ok auth-stamp stamp-in">Accepted {stampTime}</span>
      )}
    </section>
  )
}

export function AuthLayout({ title, children }) {
  const sideRef = useRef(null)

  // The sample card leans toward the pointer.
  useEffect(() => {
    const side = sideRef.current
    if (!side || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined
    const onMove = (e) => {
      const r = side.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      side.style.setProperty('--tilt-x', `${(-y * 10).toFixed(2)}deg`)
      side.style.setProperty('--tilt-y', `${(x * 14).toFixed(2)}deg`)
    }
    const onLeave = () => {
      side.style.setProperty('--tilt-x', '0deg')
      side.style.setProperty('--tilt-y', '0deg')
    }
    side.addEventListener('pointermove', onMove)
    side.addEventListener('pointerleave', onLeave)
    return () => {
      side.removeEventListener('pointermove', onMove)
      side.removeEventListener('pointerleave', onLeave)
    }
  }, [])

  return (
    <div className="auth">
      <aside className="auth-side" ref={sideRef} aria-hidden="true">
        <CatalogScene className="auth-scene" />
        <div className="auth-brand">
          <BrandMark size={88} label="Yes Officer" />
        </div>
        <div className="auth-sample">
          <div className="auth-tilt">
            <LiveSampleCard />
          </div>
          <p className="auth-line">
            <span>Every answer moves you forward.</span> <span>Take your best shot.</span>
          </p>
        </div>
      </aside>
      <main className="auth-main">
        <div className="auth-form">
          <h1>{title}</h1>
          {children}
        </div>
        <SiteFooter className="site-footer-auth" />
      </main>
    </div>
  )
}
