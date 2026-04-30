import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title:       'ResearchMind',
  description: 'Scientific research analysis with AI agent',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>{children}</body>
    </html>
  )
}
