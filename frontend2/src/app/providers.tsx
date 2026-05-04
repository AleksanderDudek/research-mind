'use client'

import { useEffect, useState } from 'react'
import { NextIntlClientProvider } from 'next-intl'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useAppStore } from '@/lib/store'
import enMessages from '@/i18n/messages/en.json'
import plMessages from '@/i18n/messages/pl.json'

const MESSAGES = { en: enMessages, pl: plMessages } as const

export default function Providers({ children }: { readonly children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
  }))

  const lang = useAppStore(s => s.lang)

  useEffect(() => {
    useAppStore.persist.rehydrate()
  }, [])

  return (
    <NextIntlClientProvider locale={lang} messages={MESSAGES[lang]}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={400}>
          {children}
          <Toaster position="bottom-center" richColors closeButton toastOptions={{ className: 'font-sans text-sm' }} />
        </TooltipProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  )
}
