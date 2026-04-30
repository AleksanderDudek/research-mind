'use client'

import { MessageSquare, PlusCircle, FileText, History, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SidebarTab } from './Sidebar'

interface Props {
  readonly tab:    SidebarTab
  readonly onTab:  (t: SidebarTab) => void
}

const TABS: { id: SidebarTab; Icon: typeof MessageSquare; label: string }[] = [
  { id: 'chat',       Icon: MessageSquare, label: 'Chat'    },
  { id: 'add-source', Icon: PlusCircle,    label: 'Add'     },
  { id: 'sources',    Icon: FileText,      label: 'Sources' },
  { id: 'history',    Icon: History,       label: 'History' },
  { id: 'settings',   Icon: Settings,      label: 'Settings'},
]

export function BottomTabs({ tab, onTab }: Props) {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 border-t border-border bg-surface/95 backdrop-blur-sm">
      <div className="flex">
        {TABS.map(({ id, Icon, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTab(id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors',
              tab === id ? 'text-brand' : 'text-slate-400 hover:text-slate-600',
            )}
          >
            <Icon size={18} strokeWidth={tab === id ? 2.5 : 1.75} />
            {label}
          </button>
        ))}
      </div>
      {/* Safe area padding for iOS */}
      <div className="h-safe-bottom" />
    </nav>
  )
}
