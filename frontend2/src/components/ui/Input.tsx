import { InputHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

type Props = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, Props>(({ className, ...rest }, ref) => (
  <input
    ref={ref}
    className={cn(
      'w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm text-slate-900',
      'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-colors',
      className,
    )}
    {...rest}
  />
))
Input.displayName = 'Input'
