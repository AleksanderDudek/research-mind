import { NextIntlClientProvider } from 'next-intl'
import { setRequestLocale } from 'next-intl/server'
import { notFound } from 'next/navigation'
import { routing } from '@/i18n/routing'
import Providers from './providers'

export default async function LocaleLayout({
  children,
  params,
}: {
  readonly children: React.ReactNode
  readonly params:   Promise<{ locale: string }>
}) {
  const { locale } = await params
  if (!(routing.locales as readonly string[]).includes(locale)) notFound()

  // Required for static export — lets next-intl know the locale without
  // reading HTTP headers (which are unavailable during static rendering).
  setRequestLocale(locale)

  // Load messages directly from params to avoid headers() calls.
  const messages = (await import(`@/i18n/messages/${locale}.json`)).default

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <Providers>{children}</Providers>
    </NextIntlClientProvider>
  )
}
