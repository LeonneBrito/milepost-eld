import L from 'leaflet'
import type { StopKind } from '@/lib/types'

const FG = '#E8EBED'
const FG_MUTED = '#8B959E'
const AMBER = '#F0A020'
const INK_900 = '#0C0E10'

function icon(html: string, size = 16) {
  return L.divIcon({
    className: '',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

const SHAPES: Record<StopKind, () => L.DivIcon> = {
  start: () =>
    icon(
      `<div style="width:12px;height:12px;border-radius:50%;background:${INK_900};border:2px solid ${FG}"></div>`,
    ),
  pickup: () =>
    icon(
      `<div style="width:12px;height:12px;border-radius:50%;background:${AMBER};border:2px solid ${INK_900}"></div>`,
    ),
  dropoff: () =>
    icon(
      `<div style="width:11px;height:11px;transform:rotate(45deg);background:${AMBER};border:2px solid ${INK_900}"></div>`,
    ),
  fuel: () =>
    icon(
      `<div style="width:10px;height:10px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:${INK_900};border:2px solid ${FG_MUTED}"></div>`,
    ),
  break_30: () =>
    icon(
      `<div style="width:12px;height:6px;border-radius:6px 6px 0 0;background:${FG_MUTED};border:2px solid ${INK_900};border-bottom:none"></div>`,
    ),
  rest_10: () =>
    icon(
      `<div style="width:12px;height:12px;border-radius:50%;background:${FG_MUTED};box-shadow:3px -1px 0 -1px ${INK_900} inset"></div>`,
    ),
  restart_34: () =>
    icon(
      `<div style="width:14px;height:14px;border-radius:50%;border:1.5px solid ${FG_MUTED};display:flex;align-items:center;justify-content:center">
         <div style="width:8px;height:8px;border-radius:50%;background:${FG_MUTED};box-shadow:2px -1px 0 -1px ${INK_900} inset"></div>
       </div>`,
      18,
    ),
}

export function stopIcon(kind: StopKind): L.DivIcon {
  return (SHAPES[kind] ?? SHAPES.pickup)()
}
