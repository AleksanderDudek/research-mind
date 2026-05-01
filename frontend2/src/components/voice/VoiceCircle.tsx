'use client'

import { motion } from 'framer-motion'
import type { LoopState } from '@/hooks/useVoiceLoop'

interface Props { readonly state: LoopState; readonly rms: number }

const COLOR: Record<LoopState, string> = {
  idle:         '#4F46E5',
  recording:    '#EF4444',
  transcribing: '#D97706',
  thinking:     '#D97706',
  speaking:     '#3B82F6',
}

export function VoiceCircle({ state, rms }: Props) {
  const color = COLOR[state]
  return (
    <div className="relative flex items-center justify-center w-32 h-32 mx-auto">
      {(state === 'recording' || state === 'speaking') && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: color, opacity: 0.15 }}
          animate={{ scale: [1, 1.6], opacity: [0.15, 0] }}
          transition={{ duration: state === 'speaking' ? 1.8 : 1.2, repeat: Infinity, ease: 'easeOut' }}
        />
      )}
      <motion.div
        className="w-24 h-24 rounded-full flex items-center justify-center shadow-lg"
        style={{ backgroundColor: color }}
        animate={{
          scale: state === 'recording' ? 1 + rms * 0.35 : 1,
          boxShadow: state === 'recording'
            ? `0 0 0 ${Math.round(rms * 18)}px ${color}33`
            : '0 8px 30px rgb(0 0 0 / .12)',
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        {(state === 'transcribing' || state === 'thinking') && (
          <motion.div
            className="w-6 h-6 rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
            style={{ borderWidth: 3, borderStyle: 'solid', borderColor: 'rgba(255,255,255,.3)', borderTopColor: '#fff' }}
          />
        )}
        {state === 'speaking' && <span className="text-white text-3xl select-none">🔊</span>}
        {state === 'idle'      && <span className="text-white text-3xl select-none">🎙️</span>}
        {state === 'recording' && <span className="text-white text-3xl select-none">🎤</span>}
      </motion.div>
    </div>
  )
}
