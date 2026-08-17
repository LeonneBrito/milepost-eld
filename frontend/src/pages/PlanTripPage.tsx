import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { Logo } from '@/components/Logo'
import { TripForm } from '@/features/trip-form/TripForm'

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'

export function PlanTripPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-8 lg:py-14">
      <Logo className="mb-10" />

      <div className="grid flex-1 gap-10 lg:grid-cols-[420px_1fr]">
        <div>
          <h1 className="mb-1.5 text-2xl font-semibold text-fg">Plan a trip</h1>
          <p className="mb-8 text-sm text-fg-muted">
            Route, stops, and FMCSA-compliant daily logs — computed server-side, in one request.
          </p>
          <TripForm />
        </div>

        <div className="relative hidden overflow-hidden rounded-xl border border-line bg-ink-800 lg:block">
          <MapContainer
            center={[39.5, -98.35]}
            zoom={4}
            className="size-full"
            zoomControl={false}
            dragging={false}
            scrollWheelZoom={false}
            doubleClickZoom={false}
            touchZoom={false}
            boxZoom={false}
            keyboard={false}
            attributionControl={false}
          >
            <TileLayer url={TILE_URL} />
          </MapContainer>
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/40 to-ink-900/10" />
        </div>
      </div>
    </div>
  )
}
