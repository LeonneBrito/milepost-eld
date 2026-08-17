import type { Stop } from '@/lib/types'
import { formatDuration, formatStopKind, formatTime } from '@/lib/format'
import { cn } from '@/lib/utils'

interface StopTimelineProps {
  stops: Stop[]
  hoveredStopSequence: number | null
  onHoverStop: (sequence: number | null) => void
}

export function StopTimeline({ stops, hoveredStopSequence, onHoverStop }: StopTimelineProps) {
  return (
    <ol className="flex flex-col gap-0.5 overflow-y-auto p-2">
      {stops.map((stop, i) => (
        <li key={stop.sequence}>
          <button
            type="button"
            onMouseEnter={() => onHoverStop(stop.sequence)}
            onMouseLeave={() => onHoverStop(null)}
            onFocus={() => onHoverStop(stop.sequence)}
            onBlur={() => onHoverStop(null)}
            className={cn(
              'flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left transition-colors duration-150',
              stop.sequence === hoveredStopSequence ? 'bg-ink-700' : 'hover:bg-ink-700/60',
            )}
          >
            <span className="mt-1 flex flex-col items-center">
              <Dot kind={stop.kind} />
              {i < stops.length - 1 && <span className="mt-0.5 h-full min-h-4 w-px bg-line" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-baseline justify-between gap-2">
                <span className="truncate text-[13px] text-fg">{formatStopKind(stop.kind)}</span>
                <span className="shrink-0 font-mono text-xs text-fg-dim tabular-nums">
                  {formatTime(stop.arrival)}
                </span>
              </span>
              <span className="block truncate text-xs text-fg-muted">{stop.label}</span>
              {stop.duration_minutes > 0 && (
                <span className="block text-xs text-fg-dim">{formatDuration(stop.duration_minutes)}</span>
              )}
            </span>
          </button>
        </li>
      ))}
    </ol>
  )
}

function Dot({ kind }: { kind: Stop['kind'] }) {
  if (kind === 'start') {
    return <span className="size-2.5 shrink-0 rounded-full border-2 border-fg bg-ink-900" />
  }
  if (kind === 'pickup' || kind === 'dropoff') {
    return <span className="size-2.5 shrink-0 rounded-full bg-amber" />
  }
  return <span className="size-2.5 shrink-0 rounded-full border-2 border-fg-muted bg-ink-900" />
}
