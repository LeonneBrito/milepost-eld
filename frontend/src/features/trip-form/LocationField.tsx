import { useQuery } from '@tanstack/react-query'
import { Check, Loader2 } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { qk } from '@/app/query-client'
import type { GeocodeResult } from '@/lib/types'
import { useDebouncedValue } from '@/lib/use-debounced-value'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface LocationFieldProps {
  id: string
  label: string
  placeholder: string
  value: string
  onChange: (value: string) => void
  onBlur: () => void
  error?: string
}

// The geocode endpoint returns a single best match (Nominatim, limit=1) and
// the backend re-geocodes from free text on submit regardless — so this is a
// confirmation hint, not a picker, and the field's value is always the raw
// text the driver typed.
export function LocationField({ id, label, placeholder, value, onChange, onBlur, error }: LocationFieldProps) {
  const debounced = useDebouncedValue(value, 350)
  const query = debounced.trim()

  const geocode = useQuery<GeocodeResult>({
    queryKey: qk.geocode(query),
    queryFn: () => api.get<GeocodeResult>(`/api/geocode/?q=${encodeURIComponent(query)}`),
    enabled: query.length >= 3,
    staleTime: Infinity,
    retry: false,
  })

  const showHint = query.length >= 3 && query === value.trim()

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        aria-invalid={!!error}
        aria-describedby={`${id}-hint`}
      />
      <div id={`${id}-hint`} className="min-h-4 text-xs">
        {error ? (
          <span className="text-alert">{error}</span>
        ) : showHint && geocode.isFetching ? (
          <span className="flex items-center gap-1 text-fg-dim">
            <Loader2 className="size-3 animate-spin" /> Looking up…
          </span>
        ) : showHint && geocode.isError ? (
          <span className="text-fg-dim">
            {geocode.error instanceof ApiError
              ? "Couldn't find that place. Try adding a state, like 'Springfield, MO'."
              : 'Could not verify that location.'}
          </span>
        ) : showHint && geocode.data ? (
          <span className="flex items-center gap-1 text-fg-dim">
            <Check className="size-3 text-amber" /> {geocode.data.label}
          </span>
        ) : null}
      </div>
    </div>
  )
}
