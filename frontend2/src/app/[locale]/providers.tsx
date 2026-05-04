'use client'

import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useAppStore } from '@/lib/store'

export default function Providers({ children }: { readonly children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
  }))

  // Rehydrate persisted preferences (ttsEnabled) after mount to avoid React #185.
  useEffect(() => {
    useAppStore.persist.rehydrate()
  }, [])


  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={400}>
        {children}
        <Toaster position="bottom-center" richColors closeButton toastOptions={{ className: 'font-sans text-sm' }} />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
