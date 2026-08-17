// Presentational-only scans over already-computed segments — these read
// positions in time the backend already decided, they never decide legality
// themselves. The HOS engine (backend/apps/hos) is the only place a break or
// reset gets inserted; this just measures where "now" (end of the rendered
// day) sits relative to those boundaries, for the meter strip.

import type { DutySegment } from '@/lib/types'

const ACTIVE = new Set(['D', 'ON'])
const QUALIFYING_BREAK_MINUTES = 30

/** Minutes from the first on-duty/driving segment to the last, this day. */
export function dutyWindowMinutes(segments: DutySegment[]): number {
  const active = segments.filter((s) => ACTIVE.has(s.status))
  if (!active.length) return 0
  const first = active[0].start_minute
  const last = active[active.length - 1].end_minute
  return last - first
}

/** Minutes of driving/on-duty accrued since the most recent break of >=30 min ended. */
export function minutesSinceLastBreak(segments: DutySegment[]): number {
  let sinceBreak = 0
  for (const seg of segments) {
    const isQualifyingBreak = (seg.status === 'OFF' || seg.status === 'SB') && seg.end_minute - seg.start_minute >= QUALIFYING_BREAK_MINUTES
    if (isQualifyingBreak) {
      sinceBreak = 0
    } else if (ACTIVE.has(seg.status)) {
      sinceBreak += seg.end_minute - seg.start_minute
    }
  }
  return sinceBreak
}
