import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full font-medium leading-none',
  {
    variants: {
      variant: {
        default:  'bg-surface-2 text-slate-600 border border-border',
        brand:    'bg-brand-light text-brand',
        success:  'bg-green-50   text-green-700',
        warning:  'bg-amber-50   text-amber-700',
        error:    'bg-red-50     text-red-600',
      },
      size: {
        sm: 'px-2   py-0.5 text-[10px]',
        md: 'px-2.5 py-1   text-xs',
      },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  },
)

interface Props
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ variant, size, className, ...rest }: Props) {
  return <span className={cn(badgeVariants({ variant, size }), className)} {...rest} />
}
