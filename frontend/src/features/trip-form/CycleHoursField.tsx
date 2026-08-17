import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface CycleHoursFieldProps {
  value: number
  onChange: (value: number) => void
  onBlur: () => void
  error?: string
}

export function CycleHoursField({ value, onChange, onBlur, error }: CycleHoursFieldProps) {
  const remaining = Math.max(0, 70 - value)

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <Label htmlFor="cycle-hours-input">Cycle hours used (70 / 8 days)</Label>
        <Input
          id="cycle-hours-input"
          type="number"
          min={0}
          max={70}
          step={0.25}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          onBlur={onBlur}
          className="h-8 w-20 text-right font-mono tabular-nums"
          aria-describedby="cycle-hours-hint"
        />
      </div>
      <Slider
        value={[value]}
        min={0}
        max={70}
        step={0.25}
        onValueChange={([v]) => onChange(v)}
        onValueCommit={onBlur}
        aria-label="Cycle hours used"
      />
      <div id="cycle-hours-hint" className="min-h-4 text-xs">
        {error ? (
          <span className="text-alert">{error}</span>
        ) : (
          <span className="text-fg-dim">{remaining.toFixed(2)} hours left in your cycle.</span>
        )}
      </div>
    </div>
  )
}
