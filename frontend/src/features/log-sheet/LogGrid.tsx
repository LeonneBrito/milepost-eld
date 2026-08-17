import type { LogDay } from '@/lib/types'
import { formatHours, formatMiles } from '@/lib/format'
import { buildDutyPath, GRID, hourTicks, minuteToX, ROW_LABELS, statusToY } from './grid-geometry'

const INK = '#16255A'

interface LogGridProps {
  logDay: LogDay
  dayLabel: string
}

export function LogGrid({ logDay, dayLabel }: LogGridProps) {
  const { x0, x1, y0, rowH, rows, remarksY } = GRID
  const gridHeight = rowH * rows.length
  const remarks = logDay.segments.filter((s) => s.remark && s.start_minute > 0)

  return (
    <svg
      viewBox={`0 0 ${GRID.viewBox.w} ${GRID.viewBox.h}`}
      style={{ width: '100%', display: 'block' }}
      role="img"
      aria-label={`Daily log grid for ${dayLabel}: duty status stepping between off duty, sleeper berth, driving and on duty across 24 hours`}
    >
      <defs>
        <pattern id="mp-log-minor" width="7.5" height={gridHeight} patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2={gridHeight} stroke={INK} strokeOpacity="0.14" strokeWidth="1" />
        </pattern>
        <pattern id="mp-log-major" width="30" height={gridHeight} patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2={gridHeight} stroke={INK} strokeOpacity="0.4" strokeWidth="1" />
        </pattern>
      </defs>

      <text x={16} y={26} fill={INK} fontSize="13" fontFamily="Overpass, sans-serif" fontWeight={600}>
        {dayLabel}
      </text>
      <text
        x={x1}
        y={26}
        fill={INK}
        fillOpacity="0.65"
        fontSize="12"
        fontFamily="Overpass, sans-serif"
        textAnchor="end"
      >
        {formatMiles(logDay.total_miles_driving)} driving
      </text>

      <rect x={x0} y={y0} width={x1 - x0} height={gridHeight} fill="url(#mp-log-minor)" />
      <rect x={x0} y={y0} width={x1 - x0} height={gridHeight} fill="url(#mp-log-major)" />
      <rect x={x0} y={y0} width={x1 - x0} height={gridHeight} fill="none" stroke={INK} strokeWidth="1.2" />

      {rows.slice(1).map((row) => (
        <line
          key={row}
          x1={x0}
          x2={x1}
          y1={y0 + rows.indexOf(row) * rowH}
          y2={y0 + rows.indexOf(row) * rowH}
          stroke={INK}
          strokeOpacity="0.55"
        />
      ))}

      {rows.map((row) => (
        <text
          key={row}
          x={x0 - 8}
          y={statusToY(row) + 4}
          fill={INK}
          fontSize="11"
          fontFamily="Overpass, sans-serif"
          textAnchor="end"
        >
          {ROW_LABELS[row]}
        </text>
      ))}

      {hourTicks().map((tick) => (
        <text
          key={tick.minute}
          x={tick.x}
          y={y0 - 7}
          fill={INK}
          fontSize="11"
          fontFamily="Overpass, sans-serif"
          textAnchor="middle"
        >
          {tick.label}
        </text>
      ))}

      <path d={buildDutyPath(logDay.segments)} fill="none" stroke={INK} strokeWidth="2.6" strokeLinejoin="miter" />

      {rows.map((row) => (
        <text
          key={row}
          x={x1 + 12}
          y={statusToY(row) + 4}
          fill={INK}
          fontSize="12"
          fontFamily="'JetBrains Mono', monospace"
        >
          {formatHours(logDay.totals[TOTAL_KEY[row]])}
        </text>
      ))}

      <text x={x0 - 8} y={remarksY + 10} fill={INK} fontSize="11" fontFamily="Overpass, sans-serif" textAnchor="end">
        Remarks
      </text>
      <line x1={x0} x2={x1} y1={remarksY} y2={remarksY} stroke={INK} strokeOpacity="0.35" />
      {remarks.map((seg, i) => (
        <text
          key={`${seg.start_minute}-${i}`}
          x={minuteToX(seg.start_minute)}
          y={remarksY + 10}
          fill={INK}
          fontSize="11"
          fontFamily="Overpass, sans-serif"
          transform={`rotate(-58 ${minuteToX(seg.start_minute)} ${remarksY + 10})`}
        >
          {seg.remark}
        </text>
      ))}
    </svg>
  )
}

const TOTAL_KEY = {
  OFF: 'off_duty',
  SB: 'sleeper',
  D: 'driving',
  ON: 'on_duty',
} as const
