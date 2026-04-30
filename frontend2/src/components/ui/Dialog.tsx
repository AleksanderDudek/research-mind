'use client'

import * as Radix from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export const Dialog       = Radix.Root
export const DialogTrigger = Radix.Trigger

export function DialogContent({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <Radix.Portal>
      <Radix.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <Radix.Content
        className={cn(
          'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2',
          'w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
          'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
          'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
          className,
        )}
      >
        {children}
        <Radix.Close className="absolute right-4 top-4 rounded-lg p-1 text-slate-400 hover:text-slate-600 transition-colors">
          <X size={16} />
        </Radix.Close>
      </Radix.Content>
    </Radix.Portal>
  )
}

export const DialogTitle       = Radix.Title
export const DialogDescription = Radix.Description
