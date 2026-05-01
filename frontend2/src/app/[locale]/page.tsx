'use client'

import { useAppStore } from '@/lib/store'
import { ContextPanel } from '@/components/context/ContextPanel'
import { ContextView }  from '@/components/context/ContextView'

export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}

export default function Home() {
  const activeContext = useAppStore(s => s.activeContext)
  return activeContext ? <ContextView /> : <ContextPanel />
}
