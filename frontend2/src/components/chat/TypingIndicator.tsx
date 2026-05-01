'use client'

import { motion } from 'framer-motion'

const DOTS = [0, 1, 2]

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex items-center gap-1.5">
        {DOTS.map(i => (
          <motion.span
            key={i}
            className="w-2 h-2 rounded-full bg-slate-300 block"
            animate={{ y: [0, -5, 0] }}
            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
          />
        ))}
      </div>
    </div>
  )
}
