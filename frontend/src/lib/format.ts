// Pure presentation formatting. No HOS decisions live here — only rendering
// values that already arrived pre-computed from the API.

/** Decimal hours -> "H:MM", e.g. 11 -> "11:00", 4.5 -> "4:30". */
export function formatHours(hours: number): string {
  const totalMinutes = Math.round(hours * 60)
  const sign = totalMinutes < 0 ? '-' : ''
  const abs = Math.abs(totalMinutes)
  const h = Math.floor(abs / 60)
  const m = abs % 60
  return `${sign}${h}:${String(m).padStart(2, '0')}`
}

/** Minutes-from-midnight -> "H:MM". */
export function formatMinutes(minutes: number): string {
  return formatHours(minutes / 60)
}

export function formatMiles(miles: number): string {
  return `${Math.round(miles).toLocaleString()} mi`
}

export function formatDate(iso: string): string {
  const date = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  if (h === 0) return `${m} min`
  if (m === 0) return `${h} hr`
  return `${h} hr ${m} min`
}

const STOP_LABELS: Record<string, string> = {
  start: 'Start',
  pickup: 'Pickup',
  dropoff: 'Dropoff',
  fuel: 'Fuel',
  break_30: '30-min break',
  rest_10: '10-hr rest',
  restart_34: '34-hr restart',
}

export function formatStopKind(kind: string): string {
  return STOP_LABELS[kind] ?? kind
}
