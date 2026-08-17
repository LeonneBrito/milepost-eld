import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api, messageFor } from '@/lib/api'
import type { TripInput, TripPlan } from '@/lib/types'
import { qk } from '@/app/query-client'

export function useCreateTrip() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (input: TripInput) => api.post<TripPlan>('/api/trips/', input),
    onSuccess: (plan) => {
      queryClient.setQueryData(qk.trip(plan.id), plan)
      navigate(`/trip/${plan.id}`)
    },
    onError: (err) => toast.error(messageFor(err)),
  })
}
