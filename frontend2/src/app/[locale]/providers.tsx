'use client'

import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'

export default function Providers({ children }: { readonly children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={400}>
        {children}
        <Toaster position="bottom-center" richColors closeButton toastOptions={{ className: 'font-sans text-sm' }} />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
