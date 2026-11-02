import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Input, Modal } from '../ui'
import { SignInFooter } from './SignInFooter'
import { loginUser } from '../../services/api'

export interface LoginButtonProps {
  fullWidth?: boolean
  onSuccess: (email: string) => void
}

export function LoginButton({ fullWidth = false, onSuccess }: LoginButtonProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return <>
    <button type="button" className={`workspace-account-action ${fullWidth ? 'w-full' : ''}`} onClick={() => { setError(''); setOpen(true) }}>
      <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5"
          d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
      </svg>
      {t('workspace.signIn')}
    </button>
    <Modal isOpen={open} onClose={() => { if (!busy) { setOpen(false); setPassword('') } }} title={t('workspace.signIn')} maxWidthClass="max-w-md">
      <form className="workspace-login" onSubmit={async event => {
        event.preventDefault()
        if (busy) return
        setBusy(true); setError('')
        try { await loginUser(email.trim(), password); onSuccess(email.trim()); setOpen(false) }
        catch (err) { setError(err instanceof Error ? err.message : t('workspace.signInFailed')) }
        finally { setBusy(false); setPassword('') }
      }}>
        <Input id="account-email" label={t('workspace.email')} type="email" autoComplete="username" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} />
        <Input id="account-password" label={t('workspace.password')} type="password" autoComplete="current-password" required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} />
        {error && <Alert type="error" message={error} />}
        <Button type="submit" isLoading={busy} fullWidth>{t('workspace.signIn')}</Button>
        <p>{t('workspace.accountHelp')}</p>
      </form>
      <SignInFooter />
    </Modal>
  </>
}
