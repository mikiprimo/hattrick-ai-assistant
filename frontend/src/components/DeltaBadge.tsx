interface Props {
  value: number
}

export function DeltaBadge({ value }: Props) {
  if (value === 0) return <span style={{ color: '#9ca3af', fontSize: 12 }}>—</span>
  const color = value > 0 ? '#16a34a' : '#dc2626'
  return (
    <span style={{ color, fontWeight: 600, fontSize: 13 }}>
      {value > 0 ? '+' : ''}{value}
    </span>
  )
}
