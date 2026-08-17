import { useEffect } from 'react'
import type { LogDay } from '@/lib/types'
import { formatHours } from '@/lib/format'
import { totalsSumHours } from './grid-geometry'
import { LogGrid } from './LogGrid'

interface LogSheetProps {
  logDay: LogDay
}

export function LogSheet({ logDay }: LogSheetProps) {
  const dayLabel = `Day ${logDay.sequence} — ${new Date(`${logDay.date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })}`

  useEffect(() => {
    if (!import.meta.env.DEV) return
    const sum = totalsSumHours(logDay.totals)
    if (Math.abs(sum - 24) > 0.01) {
      // eslint-disable-next-line no-console
      console.error(`LogSheet: day ${logDay.sequence} totals ${sum}h, expected 24:00`, logDay)
    }
  }, [logDay])

  return (
    <div className="print-sheet rounded-md bg-paper px-1 pb-0.5 pt-1.5">
      <LogGrid logDay={logDay} dayLabel={dayLabel} />

      <table className="sr-only">
        <caption>{dayLabel} — duty status segments and daily totals</caption>
        <thead>
          <tr>
            <th scope="col">Status</th>
            <th scope="col">Start</th>
            <th scope="col">End</th>
            <th scope="col">Remark</th>
          </tr>
        </thead>
        <tbody>
          {logDay.segments.map((seg, i) => (
            <tr key={i}>
              <td>{ROW_NAME[seg.status]}</td>
              <td>{formatHours(seg.start_minute / 60)}</td>
              <td>{formatHours(seg.end_minute / 60)}</td>
              <td>{seg.remark || '—'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td>Off duty total</td>
            <td colSpan={3}>{formatHours(logDay.totals.off_duty)}</td>
          </tr>
          <tr>
            <td>Sleeper berth total</td>
            <td colSpan={3}>{formatHours(logDay.totals.sleeper)}</td>
          </tr>
          <tr>
            <td>Driving total</td>
            <td colSpan={3}>{formatHours(logDay.totals.driving)}</td>
          </tr>
          <tr>
            <td>On duty (not driving) total</td>
            <td colSpan={3}>{formatHours(logDay.totals.on_duty)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

const ROW_NAME = {
  OFF: 'Off duty',
  SB: 'Sleeper berth',
  D: 'Driving',
  ON: 'On duty (not driving)',
} as const
