import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'

export const qk = {
  trip: (id: string) => ['trip', id] as const,
  geocode: (q: string) => ['geocode', q] as const,
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => (err instanceof ApiError && err.status < 500 ? false : count < 2),
    },
  },
})
