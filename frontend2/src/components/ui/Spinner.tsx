import { clsx } from 'clsx'

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={clsx('inline-block w-4 h-4 rounded-full border-2 border-indigo-300 border-t-indigo-600 animate-spin', className)}
      aria-label="loading"
    />
  )
}
