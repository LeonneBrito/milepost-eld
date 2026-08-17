import { Marker, Popup } from 'react-leaflet'
import type { Stop } from '@/lib/types'
import { formatDuration, formatMiles, formatStopKind, formatTime } from '@/lib/format'
import { stopIcon } from './stop-icons'

interface StopMarkerProps {
  stop: Stop
  isHovered: boolean
  onHover: (sequence: number | null) => void
}

export function StopMarker({ stop, isHovered, onHover }: StopMarkerProps) {
  return (
    <Marker
      position={[stop.lat, stop.lon]}
      icon={stopIcon(stop.kind)}
      zIndexOffset={isHovered ? 1000 : 0}
      eventHandlers={{
        mouseover: () => onHover(stop.sequence),
        mouseout: () => onHover(null),
      }}
    >
      <Popup>
        <div className="mp text-[13px]">
          <div className="font-semibold text-ink">
            {formatStopKind(stop.kind)} — {stop.label}
          </div>
          <div className="mt-1 text-ink/70">
            Arrive {formatTime(stop.arrival)}
            {stop.duration_minutes > 0 && ` · ${formatDuration(stop.duration_minutes)}`}
          </div>
          <div className="text-ink/70">{formatMiles(stop.distance_from_origin_miles)} from origin</div>
        </div>
      </Popup>
    </Marker>
  )
}
