import logoMark from '../assets/brand/yes-officer-mark.png'

/** The Yes Officer logo tile (official brand asset, used as supplied). */
export function BrandMark({ size = 36, label = null }) {
  return (
    <img
      className="brand-logo"
      src={logoMark}
      width={size}
      height={size}
      alt={label ?? ''}
      aria-hidden={label ? undefined : 'true'}
      decoding="async"
    />
  )
}
