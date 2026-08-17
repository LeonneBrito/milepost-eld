// Pure geometry for the FMCSA daily log grid. No HOS logic — segments arrive
// pre-computed from the API; this module only maps them to SVG coordinates.

import type { DutySegment, DutyStatus } from '@/lib/types'

export const GRID = {
  viewBox: { w: 900, h: 250 },
  x0: 110,
  x1: 830, // 720px across 1440 minutes -> 0.5 px/min
  y0: 56,
  rowH: 30, // 4 rows -> 120px tall
  rows: ['OFF', 'SB', 'D', 'ON'] as const satisfies readonly DutyStatus[],
  remarksY: 182,
} as const

export const ROW_LABELS: Record<DutyStatus, string> = {
  OFF: 'Off duty',
  SB: 'Sleeper',
  D: 'Driving',
  ON: 'On duty',
}

export const minuteToX = (m: number): number => GRID.x0 + (m * (GRID.x1 - GRID.x0)) / 1440

export const statusToY = (s: DutyStatus): number =>
  GRID.y0 + GRID.rows.indexOf(s) * GRID.rowH + GRID.rowH / 2

/**
 * One <path> for the whole day: horizontal runs at the row's centre line,
 * vertical connectors at each status change — exactly how a driver draws it.
 */
export function buildDutyPath(segments: DutySegment[]): string {
  if (!segments.length) return ''
  const parts = [`M${minuteToX(segments[0].start_minute)},${statusToY(segments[0].status)}`]
  segments.forEach((seg, i) => {
    if (i > 0) parts.push(`V${statusToY(seg.status)}`)
    parts.push(`H${minuteToX(seg.end_minute)}`)
  })
  return parts.join(' ')
}

export interface HourTick {
  minute: number
  x: number
  label: string
}

const HOUR_LABELS = [
  'Mid', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
  'Noon', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', 'Mid',
]

/** Every-2-hour ticks across the 24h axis, labeled the way the paper form is. */
export function hourTicks(): HourTick[] {
  const ticks: HourTick[] = []
  for (let h = 0; h <= 24; h += 2) {
    ticks.push({ minute: h * 60, x: minuteToX(h * 60), label: HOUR_LABELS[h] })
  }
  return ticks
}

/** Sum of segment totals should equal 24:00 — checked in dev, not enforced. */
export function totalsSumHours(totals: { off_duty: number; sleeper: number; driving: number; on_duty: number }): number {
  return totals.off_duty + totals.sleeper + totals.driving + totals.on_duty
}
