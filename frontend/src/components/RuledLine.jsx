import { useSnapToRule } from '../lib/useSnapToRule'

/**
 * A single line of text inside an `.index-card` that lands on the card's next
 * ruled line, however tall the content above it is.
 */
export function RuledLine({ as: Tag = 'p', gap = 12, className, style, children, ...rest }) {
  const ref = useSnapToRule(gap)
  return (
    <Tag
      ref={ref}
      className={className}
      style={{ fontSize: 'var(--t-sm)', lineHeight: 'var(--pitch)', ...style }}
      {...rest}
    >
      {children}
    </Tag>
  )
}
