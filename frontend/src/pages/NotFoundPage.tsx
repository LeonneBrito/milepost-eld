import { Link } from 'react-router-dom'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <Logo />
      <div>
        <h1 className="text-lg text-fg">That page doesn't exist.</h1>
        <p className="mt-1 text-sm text-fg-muted">Check the link, or plan a new trip.</p>
      </div>
      <Button asChild>
        <Link to="/">Plan a new trip</Link>
      </Button>
    </div>
  )
}
