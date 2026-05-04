'use client'

import { MessageSquare, FileText, History, Settings, Languages, LogOut, ShieldCheck } from 'lucide-react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { supabase } from '@/lib/supabase'
import { useAppStore } from '@/lib/store'
import type { Context } from '@/lib/types'

export type SidebarTab = 'chat' | 'sources' | 'history' | 'settings'

interface Props {
  readonly ctx:         Context
  readonly tab:         SidebarTab
  readonly sourceCount: number
  readonly onTab:       (t: SidebarTab) => void
  readonly onBack:      () => void
}

const NAV: { id: SidebarTab; Icon: typeof MessageSquare; labelKey: string; badge?: (n: number) => string }[] = [
  { id: 'chat',     Icon: MessageSquare, labelKey: 'chat'    },
  { id: 'sources',  Icon: FileText,      labelKey: 'sources', badge: String },
  { id: 'history',  Icon: History,       labelKey: 'history' },
  { id: 'settings', Icon: Settings,      labelKey: 'settings'},
]

export function Sidebar({ ctx, tab, sourceCount, onTab, onBack }: Props) {
  const t       = useTranslations()
  const lang    = useAppStore(s => s.lang)
  const setLang = useAppStore(s => s.setLang)
  const role    = useAppStore(s => s.role)

  const handleSignOut = async () => {
    await supabase.auth.signOut()
  }

  return (
    <aside className="hidden md:flex flex-col w-sidebar shrink-0 border-r bg-card h-dvh sticky top-0">
      <div className="px-4 py-4 border-b">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary mb-3 transition-colors"
        >
          ← {t('back')}
        </button>
        <p className="font-semibold text-sm truncate leading-tight">{ctx.name}</p>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ id, Icon, labelKey, badge }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTab(id)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
              tab === id ? 'bg-accent text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            <Icon size={16} className="shrink-0" />
            <span className="flex-1">{t(labelKey)}</span>
            {badge && sourceCount > 0 && (
              <span className="text-xs bg-accent text-primary rounded-full px-1.5 py-0.5 leading-none">
                {badge(sourceCount)}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="px-4 py-3 border-t space-y-2">
        {/* Admin / superadmin link */}
        {(role === 'admin' || role === 'superadmin') && (
          <Link
            href={role === 'superadmin' ? '/superadmin' : '/admin'}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            <ShieldCheck size={14} />
            {role === 'superadmin' ? t('superAdminPanel') : t('adminPanel')}
          </Link>
        )}

        {/* Language toggle */}
        <button
          type="button"
          onClick={() => setLang(lang === 'en' ? 'pl' : 'en')}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors w-full"
        >
          <Languages size={14} />
          {t('langToggle')}
        </button>

        {/* Sign out */}
        <button
          type="button"
          onClick={handleSignOut}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-destructive transition-colors w-full"
        >
          <LogOut size={14} />
          {t('authSignOut')}
        </button>
      </div>
    </aside>
  )
}
