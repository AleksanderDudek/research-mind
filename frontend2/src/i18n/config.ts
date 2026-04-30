'use client'

import { createContext, useContext } from 'react'
import type { Lang } from '@/lib/types'
import en from './en.json'
import pl from './pl.json'

type Translations = typeof en

const TRANSLATIONS: Record<Lang, Translations> = { en, pl }

export function t(lang: Lang, key: keyof Translations, vars?: Record<string, string | number>): string {
  let str = TRANSLATIONS[lang][key] ?? key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      str = str.replace(`{${k}}`, String(v))
    }
  }
  return str
}

export const LangContext = createContext<Lang>('en')
export const useLang = () => useContext(LangContext)
export const useT = () => {
  const lang = useLang()
  return (key: keyof Translations, vars?: Record<string, string | number>) => t(lang, key, vars)
}
