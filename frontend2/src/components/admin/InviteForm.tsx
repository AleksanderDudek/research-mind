'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { org as orgApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input  } from '@/components/ui/input'

export function InviteForm() {
  const t = useTranslations()
  const [email,   setEmail]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    try {
      await orgApi.invite(email.trim())
      toast.success(t('adminInviteSent', { email: email.trim() }))
      setEmail('')
    } catch (err) {
      toast.error(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleInvite} className="flex gap-2">
      <Input
        type="email"
        placeholder={t('authEmail')}
        value={email}
        onChange={e => setEmail(e.target.value)}
        required
        className="flex-1"
      />
      <Button type="submit" disabled={loading || !email.trim()}>
        {loading ? '…' : t('adminInvite')}
      </Button>
    </form>
  )
}
