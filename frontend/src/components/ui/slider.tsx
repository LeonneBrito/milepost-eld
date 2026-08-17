import * as SliderPrimitive from '@radix-ui/react-slider'
import { cn } from '@/lib/utils'

export function Slider({
  className,
  ...props
}: React.ComponentProps<typeof SliderPrimitive.Root>) {
  return (
    <SliderPrimitive.Root
      className={cn('relative flex w-full touch-none select-none items-center', className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-ink-700">
        <SliderPrimitive.Range className="absolute h-full bg-amber" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        className="block size-4 rounded-full border-2 border-amber bg-ink-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:ring-offset-2 focus-visible:ring-offset-ink-900"
        aria-label="Cycle hours used"
      />
    </SliderPrimitive.Root>
  )
}
