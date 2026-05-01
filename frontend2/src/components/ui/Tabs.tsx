'use client'

import * as Radix from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'

export const Tabs = Radix.Root

export function TabsList({ className, ...props }: Radix.TabsListProps) {
  return (
    <Radix.List
      className={cn('flex border-b border-slate-100', className)}
      {...props}
    />
  )
}

export function TabsTrigger({ className, ...props }: Radix.TabsTriggerProps) {
  return (
    <Radix.Trigger
      className={cn(
        'flex-1 py-2.5 text-sm font-medium transition-colors border-b-2 border-transparent',
        'text-slate-500 hover:text-slate-700',
        'data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-600',
        className,
      )}
      {...props}
    />
  )
}

export function TabsContent({ className, ...props }: Radix.TabsContentProps) {
  return (
    <Radix.Content
      className={cn('flex-1 overflow-hidden focus-visible:outline-none', className)}
      {...props}
    />
  )
}
