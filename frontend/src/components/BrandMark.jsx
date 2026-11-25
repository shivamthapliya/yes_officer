import { Vote } from 'lucide-react'

/** Generic app mark: a ballot-box icon on a canary tile. */
export function BrandMark({ size = 36, label = null }) {
  return (
    <span
      className="brand-logo"
      style={{ width: size, height: size }}
      role={label ? 'img' : undefined}
      aria-label={label ?? undefined}
      aria-hidden={label ? undefined : 'true'}
    >
      <Vote size={Math.round(size * 0.6)} strokeWidth={2.25} aria-hidden="true" />
    </span>
  )
}
