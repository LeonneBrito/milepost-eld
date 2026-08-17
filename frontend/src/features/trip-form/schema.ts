import { z } from 'zod'

export const tripSchema = z.object({
  current_location: z.string().min(3, 'Enter a city or address'),
  pickup_location: z.string().min(3, 'Enter a city or address'),
  dropoff_location: z.string().min(3, 'Enter a city or address'),
  current_cycle_used_hours: z
    .number()
    .min(0, 'Cannot be negative')
    .lt(70, 'At 70 hours you need a 34-hour restart before driving'),
})

export type TripFormValues = z.infer<typeof tripSchema>

export const defaultTripFormValues: TripFormValues = {
  current_location: '',
  pickup_location: '',
  dropoff_location: '',
  current_cycle_used_hours: 0,
}
