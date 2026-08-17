import { useEffect, useState } from 'react'
import type { LogDay } from '@/lib/types'
import { cn } from '@/lib/utils'
import { LogSheet } from './LogSheet'

/** True only for the brief window the browser's print dialog is open. */
function usePrinting() {
  const [isPrinting, setIsPrinting] = useState(false)
  useEffect(() => {
    const onBeforePrint = () => setIsPrinting(true)
    const onAfterPrint = () => setIsPrinting(false)
    window.addEventListener('beforeprint', onBeforePrint)
    window.addEventListener('afterprint', onAfterPrint)
    return () => {
      window.removeEventListener('beforeprint', onBeforePrint)
      window.removeEventListener('afterprint', onAfterPrint)
    }
  }, [])
  return isPrinting
}

interface LogSheetPagerProps {
  logs: LogDay[]
  activeIndex: number
  onActiveIndexChange: (index: number) => void
}

export function LogSheetPager({ logs, activeIndex, onActiveIndexChange }: LogSheetPagerProps) {
  const active = logs[activeIndex]
  const isPrinting = usePrinting()

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return
      if (e.key === 'ArrowLeft') onActiveIndexChange(Math.max(0, activeIndex - 1))
      if (e.key === 'ArrowRight') onActiveIndexChange(Math.min(logs.length - 1, activeIndex + 1))
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [activeIndex, logs.length, onActiveIndexChange])

  if (!active) return null

  return (
    <div>
      <div className="mb-2.5 flex items-center gap-2.5">
        <span className="text-[13px] text-fg">Daily log</span>
        <span className="text-xs text-fg-muted">
          Day {activeIndex + 1} of {logs.length}
        </span>
        <div className="ml-auto flex gap-1.5 no-print" role="tablist" aria-label="Select log day">
          {logs.map((log, i) => (
            <button
              key={log.sequence}
              type="button"
              role="tab"
              aria-selected={i === activeIndex}
              onClick={() => onActiveIndexChange(i)}
              className={cn(
                'size-[26px] rounded border text-xs font-medium transition-colors duration-150',
                i === activeIndex
                  ? 'border-amber bg-amber text-ink-900'
                  : 'border-line bg-ink-700 text-fg-muted hover:text-fg',
              )}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>

      {isPrinting ? (
        logs.map((log) => <LogSheet key={log.sequence} logDay={log} />)
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-160">
            <LogSheet logDay={active} />
          </div>
        </div>
      )}
    </div>
  )
}
