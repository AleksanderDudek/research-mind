'use client'

/**
 * RouteGuard — centralised, flash-free route protection.
 *
 * Render this as the outermost wrapper of any protected page component.
 * While auth is still loading (authReady === false) a neutral spinner is shown
 * instead of the protected content — eliminating the "flash of unauthorized
 * content" that happens when a useEffect-based redirect fires after the first
 * render.
 *
 * Once authReady is true the guard either:
 *  - renders children (role matches)
 *  - redirects and renders nothing (role mismatch)
 *
 * Role hierarchy enforced:
 *  require="auth"        any logged-in user
 *  require="admin"       admin or superadmin
 *  require="superadmin"  superadmin only
 */

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

type Requirement = 'auth' | 'admin' | 'superadmin'

interface Props {
  readonly children:  React.ReactNode
  readonly require?:  Requirement   // default: 'auth'
  readonly redirectTo?: string      // default: '/'
}

function _isAllowed(role: string | null, requirement: Requirement): boolean {
  if (!role) return false
  switch (requirement) {
    case 'auth':        return true
    case 'admin':       return role === 'admin' || role === 'superadmin'
    case 'superadmin':  return role === 'superadmin'
  }
}

export function RouteGuard({ children, require: req = 'auth', redirectTo = '/' }: Props) {
  const router    = useRouter()
  const authReady = useAppStore(s => s.authReady)
  const role      = useAppStore(s => s.role)

  const allowed = authReady ? _isAllowed(role, req) : null  // null = still loading

  useEffect(() => {
    if (allowed === false) {
      // Redirect to login when unauthenticated; elsewhere for wrong role
      const target = role === null ? '/auth/login' : redirectTo
      router.replace(target)
    }
  }, [allowed, role, redirectTo, router])

  // Show spinner while auth is initialising or while redirect is in flight
  if (allowed !== true) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <p className="text-muted-foreground animate-pulse">Loading…</p>
      </div>
    )
  }

  return <>{children}</>
}
