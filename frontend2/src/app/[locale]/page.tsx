import { setRequestLocale } from 'next-intl/server'
import HomeClient from './_HomeClient'

export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}

export default async function Page({ params }: { readonly params: Promise<{ locale: string }> }) {
  const { locale } = await params
  setRequestLocale(locale)
  return <HomeClient />
}
