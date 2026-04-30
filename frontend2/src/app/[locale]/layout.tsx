'use client'

import { use } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/Tooltip'
import { LangContext } from '@/i18n/config'
import type { Lang } from '@/lib/types'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

export default function LocaleLayout({
  children,
  params,
}: {
  readonly children: React.ReactNode
  readonly params:   Promise<{ locale: string }>
}) {
  const { locale } = use(params)
  const lang = (locale === 'pl' ? 'pl' : 'en') as Lang

  return (
    <LangContext.Provider value={lang}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          {children}
          <Toaster
            position="bottom-center"
            richColors
            closeButton
            toastOptions={{ className: 'font-sans text-sm' }}
          />
        </TooltipProvider>
      </QueryClientProvider>
    </LangContext.Provider>
  )
}
