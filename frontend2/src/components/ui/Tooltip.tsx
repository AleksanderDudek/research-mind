'use client'

import * as Radix from '@radix-ui/react-tooltip'
import { cn } from '@/lib/utils'

export const TooltipProvider = Radix.Provider

export function Tooltip({
  children,
  content,
  side = 'top',
}: {
  children: React.ReactNode
  content:  React.ReactNode
  side?:    'top' | 'bottom' | 'left' | 'right'
}) {
  return (
    <Radix.Root delayDuration={400}>
      <Radix.Trigger asChild>{children}</Radix.Trigger>
      <Radix.Portal>
        <Radix.Content
          side={side}
          sideOffset={6}
          className={cn(
            'z-50 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs text-white shadow-md',
            'animate-in fade-in-0 zoom-in-95',
          )}
        >
          {content}
          <Radix.Arrow className="fill-slate-900" />
        </Radix.Content>
      </Radix.Portal>
    </Radix.Root>
  )
}
