import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Printer, Share2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, ApiError } from '@/lib/api'
import { qk } from '@/app/query-client'
import type { TripPlan } from '@/lib/types'
import { formatMiles } from '@/lib/format'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { HosMeters } from '@/features/hos-meters/HosMeters'
import { RouteMap } from '@/features/route-map/RouteMap'
import { StopTimeline } from '@/features/stop-timeline/StopTimeline'
import { LogSheetPager } from '@/features/log-sheet/LogSheetPager'

export function TripPage() {
  const { id } = useParams<{ id: string }>()
  const [activeDayIndex, setActiveDayIndex] = useState(0)
  const [hoveredStopSequence, setHoveredStopSequence] = useState<number | null>(null)

  const { data: trip, isPending, isError, error, refetch } = useQuery({
    queryKey: qk.trip(id!),
    queryFn: () => api.get<TripPlan>(`/api/trips/${id}/`),
    enabled: !!id,
  })

  if (isPending) return <TripPageSkeleton />

  if (isError) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <CenteredMessage title="That plan isn't available anymore.">
          <Button asChild>
            <Link to="/">Plan a new trip</Link>
          </Button>
        </CenteredMessage>
      )
    }
    return (
      <CenteredMessage title="The planner couldn't load that route.">
        <Button onClick={() => refetch()}>Try again</Button>
      </CenteredMessage>
    )
  }

  if (!trip) return null

  const routeLabel = ['start', 'pickup', 'dropoff']
    .map((kind) => trip.stops.find((s) => s.kind === kind)?.label)
    .filter(Boolean)
    .join('  →  ')

  const activeDay = trip.logs[Math.min(activeDayIndex, trip.logs.length - 1)]

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-6">
      <div className="overflow-hidden rounded-xl border border-line bg-ink-800">
        <header className="no-print flex items-center gap-3.5 border-b border-line px-4.5 py-3.5">
          <Logo />
          <span className="ml-auto truncate text-[13px] text-fg-muted">{routeLabel}</span>
          <span className="hidden shrink-0 font-mono text-xs text-fg-dim sm:inline">
            {formatMiles(trip.summary.total_distance_miles)}
          </span>
        </header>

        {activeDay && (
          <div className="no-print">
            <HosMeters logDay={activeDay} summary={trip.summary} />
          </div>
        )}

        <div className="no-print grid gap-px border-b border-line bg-line lg:grid-cols-[3fr_2fr]">
          <div className="h-70 bg-ink-800 lg:h-100">
            <RouteMap
              geometry={trip.route.geometry}
              stops={trip.stops}
              hoveredStopSequence={hoveredStopSequence}
              onHoverStop={setHoveredStopSequence}
            />
          </div>
          <div className="h-70 bg-ink-800 lg:h-100">
            <StopTimeline
              stops={trip.stops}
              hoveredStopSequence={hoveredStopSequence}
              onHoverStop={setHoveredStopSequence}
            />
          </div>
        </div>

        <div className="px-4.5 py-4.5">
          <div className="no-print mb-2 flex justify-end gap-1.5">
            <Button variant="ghost" size="icon" title="Print daily logs" onClick={() => window.print()}>
              <Printer />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Copy shareable link"
              onClick={() => {
                void navigator.clipboard.writeText(window.location.href)
                toast.success('Link copied')
              }}
            >
              <Share2 />
            </Button>
          </div>
          <LogSheetPager logs={trip.logs} activeIndex={activeDayIndex} onActiveIndexChange={setActiveDayIndex} />
        </div>
      </div>
    </div>
  )
}

function TripPageSkeleton() {
  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-6">
      <div className="overflow-hidden rounded-xl border border-line bg-ink-800">
        <div className="flex items-center gap-3.5 border-b border-line px-4.5 py-3.5">
          <Logo />
        </div>
        <div className="grid grid-cols-2 gap-px border-b border-line bg-line lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-2 bg-ink-800 px-4 py-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-1.5 w-full" />
            </div>
          ))}
        </div>
        <div className="grid gap-px border-b border-line bg-line lg:grid-cols-[3fr_2fr]">
          <Skeleton className="h-70 rounded-none lg:h-100" />
          <Skeleton className="h-70 rounded-none lg:h-100" />
        </div>
        <div className="px-4.5 py-4.5">
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    </div>
  )
}

function CenteredMessage({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo />
      <p className="text-fg">{title}</p>
      {children}
    </div>
  )
}
