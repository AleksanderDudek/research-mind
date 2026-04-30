import { cva, type VariantProps } from 'class-variance-authority'
import { ButtonHTMLAttributes, forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 rounded-md font-medium',
    'transition-all duration-150 ease-rm',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60 focus-visible:ring-offset-1',
    'disabled:pointer-events-none disabled:opacity-40',
    'select-none',
  ],
  {
    variants: {
      variant: {
        primary:   'bg-brand text-white hover:bg-brand-hover active:scale-[0.98] shadow-sm',
        secondary: 'border border-border bg-surface text-slate-700 hover:bg-surface-2 active:scale-[0.98]',
        ghost:     'text-slate-600 hover:bg-surface-2 hover:text-slate-800',
        danger:    'border border-red-200 bg-red-50 text-red-600 hover:bg-red-100',
        link:      'text-brand underline-offset-4 hover:underline p-0 h-auto',
      },
      size: {
        xs: 'h-7  px-2.5 text-xs gap-1',
        sm: 'h-8  px-3   text-sm',
        md: 'h-9  px-4   text-sm',
        lg: 'h-11 px-5   text-base',
        icon: 'h-9 w-9 p-0',
        'icon-sm': 'h-7 w-7 p-0',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

interface Props
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  readonly loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant, size, className, loading, disabled, children, ...rest }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 size={14} className="animate-spin shrink-0" />}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
