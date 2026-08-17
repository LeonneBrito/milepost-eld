import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-3.5', className)}>
      <span className="flex gap-1" aria-hidden="true">
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i} className="h-3 w-[7px] rounded-[1px] bg-amber" />
        ))}
      </span>
      <span className="text-[15px] font-semibold tracking-wide text-fg">Milepost</span>
    </span>
  )
}
