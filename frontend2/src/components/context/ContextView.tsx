'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence } from 'framer-motion'
import { sources as srcApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { Sidebar, type SidebarTab } from '@/components/layout/Sidebar'
import { BottomTabs } from '@/components/layout/BottomTabs'
import { ChatView }    from '@/components/chat/ChatView'
import { IngestPanel } from '@/components/ingest/IngestPanel'
import { VoiceMode }   from '@/components/voice/VoiceMode'
import { HistoryPanel } from './HistoryPanel'
import { SettingsPanel } from './SettingsPanel'

export function ContextView() {
  const ctx       = useAppStore(s => s.activeContext)!
  const setActive = useAppStore(s => s.setActiveContext)

  const [tab,     setTab]     = useState<SidebarTab>('chat')
  const [voiceOn, setVoiceOn] = useState(false)

  const { data: srcs = [] } = useQuery({
    queryKey: ['sources', ctx.context_id],
    queryFn:  () => srcApi.list(ctx.context_id),
    staleTime: 60_000,
  })

  const back = () => setActive(null)

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--color-bg)]">
      {/* Desktop sidebar */}
      <Sidebar
        ctx={ctx}
        tab={tab}
        sourceCount={srcs.length}
        onTab={setTab}
        onBack={back}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden pb-14 md:pb-0">
        {/* Mobile header */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-surface">
          <button type="button" onClick={back} className="text-sm text-slate-500 hover:text-brand transition-colors">
            ← Back
          </button>
          <p className="flex-1 font-semibold text-slate-800 text-sm truncate">{ctx.name}</p>
        </div>

        {/* Panel content */}
        <div className="flex-1 overflow-hidden">
          {tab === 'chat'       && <ChatView onVoiceOpen={() => setVoiceOn(true)} />}
          {tab === 'add-source' && <IngestPanel />}
          {tab === 'sources'    && <IngestPanel />}
          {tab === 'history'    && <HistoryPanel />}
          {tab === 'settings'   && <SettingsPanel />}
        </div>
      </main>

      {/* Mobile bottom tabs */}
      <BottomTabs tab={tab} onTab={setTab} />

      {/* Voice overlay */}
      <AnimatePresence>
        {voiceOn && <VoiceMode key="voice" onClose={() => setVoiceOn(false)} />}
      </AnimatePresence>
    </div>
  )
}
