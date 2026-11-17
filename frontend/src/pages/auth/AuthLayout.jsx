import { BrandMark } from '../../components/BrandMark'
import { OptionRow } from '../../components/QuestionCard'

const SAMPLE = {
  prompt: 'Which organelle produces most of a cell’s ATP?',
  options: [
    { id: 'a', position: 0, label: 'Nucleus' },
    { id: 'b', position: 1, label: 'Mitochondrion' },
    { id: 'c', position: 2, label: 'Ribosome' },
  ],
}

export function AuthLayout({ title, children }) {
  return (
    <div className="auth">
      <aside className="auth-side" aria-hidden="true">
        <div className="auth-brand">
          <BrandMark size={88} label="Yes Officer" />
        </div>
        <div className="auth-sample">
          <section className="index-card compact">
            <div className="card-head">
              <span className="call-no">Q 2 OF 5</span>
              <span className="call-no">00:41 LEFT</span>
            </div>
            <div className="card-rule">
              <i style={{ transform: 'scaleX(0.55)' }} />
            </div>
            <p className="card-prompt">
              {SAMPLE.prompt}
            </p>
            <div className="options" style={{ gridTemplateColumns: '1fr' }}>
              {SAMPLE.options.map((o) => (
                <OptionRow key={o.id} option={o} state={o.id === 'b' ? 'chosen' : undefined} />
              ))}
            </div>
            <span className="stamp stamp-ok auth-stamp">Accepted 10:42:07</span>
          </section>
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
      </main>
    </div>
  )
}
