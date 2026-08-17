import { useEffect, useState } from 'react'
import { useForm } from '@tanstack/react-form'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LocationField } from './LocationField'
import { CycleHoursField } from './CycleHoursField'
import { defaultTripFormValues, tripSchema } from './schema'
import { useCreateTrip } from './useCreateTrip'

function firstError(errors: unknown[]): string | undefined {
  const e = errors[0]
  if (e == null) return undefined
  if (typeof e === 'string') return e
  if (typeof e === 'object' && 'message' in e) return String((e as { message: unknown }).message)
  return String(e)
}

export function TripForm() {
  const createTrip = useCreateTrip()
  const [isSlow, setIsSlow] = useState(false)

  useEffect(() => {
    if (!createTrip.isPending) {
      setIsSlow(false)
      return
    }
    const id = setTimeout(() => setIsSlow(true), 3000)
    return () => clearTimeout(id)
  }, [createTrip.isPending])

  const form = useForm({
    defaultValues: defaultTripFormValues,
    validators: { onChange: tripSchema },
    onSubmit: async ({ value }) => {
      await createTrip.mutateAsync(value)
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        e.stopPropagation()
        void form.handleSubmit()
      }}
      className="flex flex-col gap-5"
    >
      <form.Field name="current_location">
        {(field) => (
          <LocationField
            id={field.name}
            label="Current location"
            placeholder="Chicago, IL"
            value={field.state.value}
            onChange={field.handleChange}
            onBlur={field.handleBlur}
            error={firstError(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Field name="pickup_location">
        {(field) => (
          <LocationField
            id={field.name}
            label="Pickup location"
            placeholder="St. Louis, MO"
            value={field.state.value}
            onChange={field.handleChange}
            onBlur={field.handleBlur}
            error={firstError(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Field name="dropoff_location">
        {(field) => (
          <LocationField
            id={field.name}
            label="Dropoff location"
            placeholder="Dallas, TX"
            value={field.state.value}
            onChange={field.handleChange}
            onBlur={field.handleBlur}
            error={firstError(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Field name="current_cycle_used_hours">
        {(field) => (
          <CycleHoursField
            value={field.state.value}
            onChange={field.handleChange}
            onBlur={field.handleBlur}
            error={firstError(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting} className="mt-1 w-full">
            {isSubmitting || createTrip.isPending ? (
              <>
                <Loader2 className="animate-spin" />
                {isSlow ? 'Waking the planner…' : 'Planning…'}
              </>
            ) : (
              'Plan trip'
            )}
          </Button>
        )}
      </form.Subscribe>
      {isSlow && (
        <p className="-mt-3 text-center text-xs text-fg-dim">
          Free hosting naps when idle — this can take up to a minute on a cold start.
        </p>
      )}
    </form>
  )
}
