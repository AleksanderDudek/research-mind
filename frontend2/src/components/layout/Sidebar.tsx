'use client'

import { MessageSquare, FileText, History, Settings, Languages } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useT, useLang } from '@/i18n/config'
import type { TranslationKey } from '@/i18n/config'
import type { Context } from '@/lib/types'

export type SidebarTab = 'chat' | 'sources' | 'history' | 'settings'

interface Props {
  readonly ctx:         Context
  readonly tab:         SidebarTab
  readonly sourceCount: number
  readonly onTab:       (t: SidebarTab) => void
  readonly onBack:      () => void
}

const NAV: { id: SidebarTab; Icon: typeof MessageSquare; labelKey: TranslationKey; badge?: (n: number) => string }[] = [
  { id: 'chat',     Icon: MessageSquare, labelKey: 'chat'    },
  { id: 'sources',  Icon: FileText,      labelKey: 'sources', badge: String },
  { id: 'history',  Icon: History,       labelKey: 'history' },
  { id: 'settings', Icon: Settings,      labelKey: 'settings'},
]

export function Sidebar({ ctx, tab, sourceCount, onTab, onBack }: Props) {
  const t    = useT()
  const lang = useLang()

  return (
    <aside className="hidden md:flex flex-col w-sidebar shrink-0 border-r border-border bg-surface h-dvh sticky top-0">
      {/* Back + context name */}
      <div className="px-4 py-4 border-b border-border">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-brand mb-3 transition-colors"
        >
          ← {t('back')}
        </button>
        <p className="font-semibold text-slate-800 text-sm truncate leading-tight">{ctx.name}</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ id, Icon, labelKey, badge }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTab(id)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
              tab === id
                ? 'bg-brand-light text-brand'
                : 'text-slate-600 hover:bg-surface-2 hover:text-slate-800',
            )}
          >
            <Icon size={16} className="shrink-0" />
            <span className="flex-1">{t(labelKey)}</span>
            {badge && sourceCount > 0 && (
              <span className="text-xs bg-brand-light text-brand rounded-full px-1.5 py-0.5 leading-none">
                {badge(sourceCount)}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Lang toggle */}
      <div className="px-4 py-3 border-t border-border">
        <a
          href={lang === 'en' ? '/pl' : '/en'}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-brand transition-colors"
        >
          <Languages size={14} />
          {t('langToggle')}
        </a>
      </div>
    </aside>
  )
}
