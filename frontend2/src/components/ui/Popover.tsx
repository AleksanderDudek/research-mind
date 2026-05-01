'use client'

import * as Radix from '@radix-ui/react-popover'
import { cn } from '@/lib/utils'

export const Popover        = Radix.Root
export const PopoverTrigger = Radix.Trigger
export const PopoverClose   = Radix.Close

export function PopoverContent({
  className,
  align = 'start',
  sideOffset = 6,
  ...props
}: Radix.PopoverContentProps) {
  return (
    <Radix.Portal>
      <Radix.Content
        align={align}
        sideOffset={sideOffset}
        className={cn(
          'z-50 min-w-[160px] rounded-lg border border-border bg-surface p-1 shadow-lg',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
          'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
          'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
          className,
        )}
        {...props}
      />
    </Radix.Portal>
  )
}

export function PopoverItem({
  className,
  destructive,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { readonly destructive?: boolean }) {
  return (
    <button
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
        destructive
          ? 'text-red-600 hover:bg-red-50'
          : 'text-slate-700 hover:bg-surface-2',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand',
        className,
      )}
      {...props}
    />
  )
}
