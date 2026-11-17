import { Link } from 'react-router-dom'

import { BrandMark } from '../components/BrandMark'

export function NotFoundPage() {
  return (
    <div className="auth-main" style={{ minHeight: '100%' }}>
      <section className="index-card" style={{ width: 'min(520px, 100%)' }}>
        <div style={{ position: 'absolute', top: -28, right: 24 }}>
          <BrandMark size={56} label="Yes Officer" />
        </div>
        <div className="card-head">
          <span className="call-no">NOT FOUND · 404</span>
        </div>
        <div className="card-rule" aria-hidden="true"><i style={{ transform: 'scaleX(0)' }} /></div>
        <h1 className="card-prompt">This card isn’t in the catalog.</h1>
        <p className="muted" style={{ margin: 'var(--s-3) 0 var(--s-5)' }}>The page may have moved, or the link is incomplete.</p>
        <Link to="/" className="btn btn-primary">Back to your room</Link>
      </section>
    </div>
  )
}
