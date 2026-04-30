'use client'

import { motion } from 'framer-motion'
import type { VoiceStatus } from '@/hooks/useVoice'

interface Props { readonly status: VoiceStatus; readonly rms: number }

const COLOR: Record<VoiceStatus, string> = {
  idle:        '#4F46E5',   // brand indigo
  recording:   '#EF4444',   // red while listening
  processing:  '#D97706',   // amber while transcribing
  confirming:  '#D97706',
}

export function VoiceCircle({ status, rms }: Props) {
  const color  = COLOR[status]
  const scale  = status === 'recording' ? 1 + rms * 0.4 : 1

  return (
    <div className="relative flex items-center justify-center w-32 h-32 mx-auto">
      {/* Outer ripple — only when recording */}
      {status === 'recording' && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: color, opacity: 0.15 }}
          animate={{ scale: [1, 1.6], opacity: [0.15, 0] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeOut' }}
        />
      )}

      {/* Main circle */}
      <motion.div
        className="w-24 h-24 rounded-full flex items-center justify-center shadow-lg"
        style={{ backgroundColor: color }}
        animate={{
          scale,
          boxShadow: status === 'recording'
            ? `0 0 0 ${Math.round(rms * 20)}px ${color}33`
            : '0 8px 30px rgb(0 0 0 / .12)',
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        {status === 'processing' || status === 'confirming' ? (
          <motion.div
            className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
            style={{ borderWidth: 3 }}
          />
        ) : (
          <span className="text-white text-3xl select-none">
            {status === 'recording' ? '🎤' : '🎙️'}
          </span>
        )}
      </motion.div>
    </div>
  )
}
