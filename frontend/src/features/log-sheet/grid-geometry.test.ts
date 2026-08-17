import { describe, expect, it } from 'vitest'
import { buildDutyPath, GRID, hourTicks, minuteToX, statusToY, totalsSumHours } from './grid-geometry'
import type { DutySegment } from '@/lib/types'

describe('minuteToX', () => {
  it('maps minute 0 to x0 and minute 1440 to x1', () => {
    expect(minuteToX(0)).toBe(GRID.x0)
    expect(minuteToX(1440)).toBe(GRID.x1)
  })

  it('maps noon to the grid midpoint', () => {
    expect(minuteToX(720)).toBe((GRID.x0 + GRID.x1) / 2)
  })
})

describe('statusToY', () => {
  it('places rows in OFF, SB, D, ON order from the top', () => {
    expect(statusToY('OFF')).toBeLessThan(statusToY('SB'))
    expect(statusToY('SB')).toBeLessThan(statusToY('D'))
    expect(statusToY('D')).toBeLessThan(statusToY('ON'))
  })

  it('centers each row within its band', () => {
    expect(statusToY('OFF')).toBe(GRID.y0 + GRID.rowH / 2)
  })
})

describe('buildDutyPath', () => {
  it('returns an empty string for no segments', () => {
    expect(buildDutyPath([])).toBe('')
  })

  it('draws a single horizontal run for one segment', () => {
    const segments: DutySegment[] = [{ status: 'OFF', start_minute: 0, end_minute: 360, remark: '' }]
    const path = buildDutyPath(segments)
    expect(path).toBe(`M${minuteToX(0)},${statusToY('OFF')} H${minuteToX(360)}`)
  })

  it('steps vertically at each status change, staying on the previous horizontal x', () => {
    const segments: DutySegment[] = [
      { status: 'OFF', start_minute: 0, end_minute: 360, remark: '' },
      { status: 'D', start_minute: 360, end_minute: 600, remark: '' },
      { status: 'ON', start_minute: 600, end_minute: 660, remark: '' },
    ]
    const path = buildDutyPath(segments)
    expect(path).toBe(
      `M${minuteToX(0)},${statusToY('OFF')} H${minuteToX(360)} V${statusToY('D')} H${minuteToX(600)} V${statusToY('ON')} H${minuteToX(660)}`,
    )
  })

  it('never draws a diagonal — every command is H or V after the initial M', () => {
    const segments: DutySegment[] = [
      { status: 'OFF', start_minute: 0, end_minute: 300, remark: '' },
      { status: 'SB', start_minute: 300, end_minute: 480, remark: '' },
      { status: 'D', start_minute: 480, end_minute: 960, remark: '' },
      { status: 'OFF', start_minute: 960, end_minute: 1440, remark: '' },
    ]
    const commands = buildDutyPath(segments).split(' ').map((token) => token[0])
    expect(commands[0]).toBe('M')
    expect(commands.slice(1).every((c) => c === 'H' || c === 'V')).toBe(true)
  })
})

describe('hourTicks', () => {
  it('spans midnight to midnight in 2-hour steps', () => {
    const ticks = hourTicks()
    expect(ticks[0]).toMatchObject({ minute: 0, label: 'Mid' })
    expect(ticks.at(-1)).toMatchObject({ minute: 1440, label: 'Mid' })
    expect(ticks).toHaveLength(13)
  })

  it('labels noon distinctly', () => {
    const noon = hourTicks().find((t) => t.minute === 720)
    expect(noon?.label).toBe('Noon')
  })
})

describe('totalsSumHours', () => {
  it('sums all four duty categories', () => {
    expect(totalsSumHours({ off_duty: 10, sleeper: 2, driving: 8, on_duty: 4 })).toBe(24)
  })
})
