import { useEffect, useRef } from 'react'
import { MapContainer, Polyline, TileLayer, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression, Polyline as LeafletPolyline } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { RouteGeometry, Stop } from '@/lib/types'
import { StopMarker } from './StopMarker'

const AMBER = '#F0A020'
const CASING = '#2A2F36'
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

interface RouteMapProps {
  geometry: RouteGeometry
  stops: Stop[]
  hoveredStopSequence: number | null
  onHoverStop: (sequence: number | null) => void
}

export function RouteMap({ geometry, stops, hoveredStopSequence, onHoverStop }: RouteMapProps) {
  const positions = geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number])

  return (
    <MapContainer
      center={positions[Math.floor(positions.length / 2)] ?? [39.5, -98.35]}
      zoom={6}
      scrollWheelZoom
      className="size-full min-h-70"
      attributionControl={false}
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
      <FitToRoute positions={positions} />
      <RoutePolyline positions={positions} />
      {stops.map((stop) => (
        <StopMarker
          key={stop.sequence}
          stop={stop}
          isHovered={stop.sequence === hoveredStopSequence}
          onHover={onHoverStop}
        />
      ))}
      <MapAttribution />
    </MapContainer>
  )
}

function FitToRoute({ positions }: { positions: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (!positions.length) return
    const bounds = positions as LatLngBoundsExpression
    map.fitBounds(bounds, { padding: [48, 48] })
  }, [map, positions])
  return null
}

const REDUCED_MOTION = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function RoutePolyline({ positions }: { positions: [number, number][] }) {
  const ref = useRef<LeafletPolyline>(null)

  useEffect(() => {
    const path = ref.current?.getElement() as SVGPathElement | undefined
    if (!path) return

    if (REDUCED_MOTION) {
      path.style.strokeDasharray = ''
      path.style.strokeDashoffset = ''
      return
    }

    const length = path.getTotalLength()
    path.style.strokeDasharray = `${length}`
    path.style.strokeDashoffset = `${length}`
    path.getBoundingClientRect() // force reflow before transition starts
    path.style.transition = 'stroke-dashoffset 900ms ease-out'
    path.style.strokeDashoffset = '0'
  }, [positions])

  return (
    <>
      <Polyline positions={positions} pathOptions={{ color: CASING, weight: 7, opacity: 0.9 }} />
      <Polyline ref={ref} positions={positions} pathOptions={{ color: AMBER, weight: 3 }} />
    </>
  )
}

function MapAttribution() {
  return (
    <div className="pointer-events-none absolute bottom-1 right-1 z-1000 rounded bg-ink-900/70 px-1.5 py-0.5 text-[10px] text-fg-muted">
      OSM &amp; CARTO
    </div>
  )
}
