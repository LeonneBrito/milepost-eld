// Mirrors backend/apps/trips/serializers.py and backend/apps/routing/views.py.
// The frontend does no HOS arithmetic — every field below arrives pre-computed.

export type DutyStatus = 'OFF' | 'SB' | 'D' | 'ON'

export type StopKind =
  | 'start'
  | 'pickup'
  | 'dropoff'
  | 'fuel'
  | 'break_30'
  | 'rest_10'
  | 'restart_34'

export interface DutySegment {
  status: DutyStatus
  start_minute: number // 0..1440, minutes from local midnight
  end_minute: number
  remark: string
}

export interface LogDayTotals {
  off_duty: number
  sleeper: number
  driving: number
  on_duty: number
}

export interface LogDay {
  date: string // YYYY-MM-DD
  sequence: number
  total_miles_driving: number
  totals: LogDayTotals
  segments: DutySegment[]
}

export interface Stop {
  sequence: number
  kind: StopKind
  label: string
  lat: number
  lon: number
  arrival: string // ISO datetime
  departure: string
  duration_minutes: number
  distance_from_origin_miles: number
}

export interface RouteGeometry {
  type: 'LineString'
  coordinates: [number, number][] // [lon, lat] pairs, travel order
}

export interface TripSummary {
  total_distance_miles: number
  total_driving_hours: number
  total_duration_hours: number
  days: number
  cycle_hours_remaining: number
  restart_required: boolean
}

export interface TripPlan {
  id: string
  summary: TripSummary
  route: { geometry: RouteGeometry }
  stops: Stop[]
  logs: LogDay[]
}

export interface TripInput {
  current_location: string
  pickup_location: string
  dropoff_location: string
  current_cycle_used_hours: number
  start_datetime?: string
  timezone?: string
}

// GeocodeView returns a single best match (Nominatim search, limit=1) —
// not a list, so LocationField confirms one candidate rather than paging a list.
export interface GeocodeResult {
  label: string
  lat: number
  lon: number
}

// Shape produced by apps/core/exceptions.py::eld_exception_handler for every error response.
export interface ApiErrorBody {
  error: string
  detail: string
  field: string | null
}
