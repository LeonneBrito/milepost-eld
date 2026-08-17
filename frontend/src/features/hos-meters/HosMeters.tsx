import type { LogDay, TripSummary } from '@/lib/types'
import { formatHours } from '@/lib/format'
import { cn } from '@/lib/utils'
import { dutyWindowMinutes, minutesSinceLastBreak } from './derive'

interface Meter {
  label: string
  usedHours: number
  maxHours: number
}

interface HosMetersProps {
  logDay: LogDay
  summary: TripSummary
}

export function HosMeters({ logDay, summary }: HosMetersProps) {
  const cycleUsedHours = 70 - summary.cycle_hours_remaining

  const meters: Meter[] = [
    { label: 'Driving today', usedHours: logDay.totals.driving, maxHours: 11 },
    { label: 'Duty window', usedHours: dutyWindowMinutes(logDay.segments) / 60, maxHours: 14 },
    { label: 'Since last break', usedHours: minutesSinceLastBreak(logDay.segments) / 60, maxHours: 8 },
    { label: 'Cycle 70 / 8 days', usedHours: cycleUsedHours, maxHours: 70 },
  ]

  return (
    <div className="grid grid-cols-2 gap-px border-b border-line bg-line lg:grid-cols-4">
      {meters.map((meter) => (
        <MeterTile key={meter.label} {...meter} />
      ))}
    </div>
  )
}

function MeterTile({ label, usedHours, maxHours }: Meter) {
  const pct = Math.min(100, Math.max(0, (usedHours / maxHours) * 100))
  const atLimit = usedHours >= maxHours
  const nearLimit = pct >= 85

  return (
    <div className="bg-ink-800 px-4 py-3">
      <div className="mb-1.5 text-[11px] text-fg-muted">{label}</div>
      <div
        className={cn(
          'mb-2 font-mono text-[17px] tabular-nums',
          atLimit ? 'text-alert' : nearLimit ? 'text-amber' : 'text-fg',
        )}
      >
        {formatHours(usedHours)}
        <span className="text-xs text-fg-dim"> / {formatHours(maxHours)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
        <div
          className={cn(
            'h-full rounded-full transition-[width] duration-300',
            atLimit ? 'bg-alert' : nearLimit ? 'bg-amber' : 'bg-fg-dim',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
