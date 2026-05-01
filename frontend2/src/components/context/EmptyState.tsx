import { BookOpen } from 'lucide-react'
import { useT } from '@/i18n/config'

export function EmptyState() {
  const t = useT()
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center gap-4">
      <div className="w-16 h-16 rounded-2xl bg-brand-light flex items-center justify-center text-brand">
        <BookOpen size={28} />
      </div>
      <div>
        <p className="font-semibold text-slate-800 mb-1">{t('noContexts')}</p>
        <p className="text-sm text-slate-500">{t('emptyContextHint')}</p>
      </div>
    </div>
  )
}
