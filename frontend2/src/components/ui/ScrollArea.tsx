'use client'

import * as Radix from '@radix-ui/react-scroll-area'
import { cn } from '@/lib/utils'

interface Props extends Radix.ScrollAreaProps {
  readonly viewportClassName?: string
}

export function ScrollArea({ className, viewportClassName, children, ...props }: Props) {
  return (
    <Radix.Root className={cn('relative overflow-hidden', className)} {...props}>
      <Radix.Viewport className={cn('h-full w-full rounded-[inherit]', viewportClassName)}>
        {children}
      </Radix.Viewport>
      <Radix.Scrollbar
        orientation="vertical"
        className="flex select-none touch-none p-0.5 transition-colors w-2.5"
      >
        <Radix.Thumb className="flex-1 bg-border rounded-full relative before:absolute before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:min-w-[44px] before:min-h-[44px]" />
      </Radix.Scrollbar>
    </Radix.Root>
  )
}
