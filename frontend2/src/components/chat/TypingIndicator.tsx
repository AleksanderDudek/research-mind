'use client'

import { motion } from 'framer-motion'

export function TypingIndicator() {
  return (
    <div className="flex gap-2.5 justify-start">
      <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center shrink-0 mt-0.5 text-xs">
        🤖
      </div>
      <div className="bg-card border rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          {[0, 1, 2].map(i => (
            <motion.span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
