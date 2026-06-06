interface Props {
  value: number
  max?: number
}

export function SkillBar({ value, max = 20 }: Props) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 80 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: '#e5e7eb',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: '#3b82f6',
            borderRadius: 3,
          }}
        />
      </div>
      <span style={{ minWidth: 18, textAlign: 'right', fontSize: 12, color: '#374151' }}>
        {value}
      </span>
    </div>
  )
}
