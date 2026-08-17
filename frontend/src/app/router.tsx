import { createBrowserRouter } from 'react-router-dom'
import { PlanTripPage } from '@/pages/PlanTripPage'
import { TripPage } from '@/pages/TripPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const router = createBrowserRouter([
  { path: '/', element: <PlanTripPage /> },
  { path: '/trip/:id', element: <TripPage /> },
  { path: '*', element: <NotFoundPage /> },
])
