import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Input, Modal } from '../ui'
import { loginUser } from '../../services/api'

export function SignIn({ onSuccess }: { onSuccess: (email: string) => void }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return <>
    <button type="button" className="workspace-account-action" onClick={() => { setError(''); setOpen(true) }}>{t('workspace.signIn')}</button>
    <Modal isOpen={open} onClose={() => { if (!busy) { setOpen(false); setPassword('') } }} title={t('workspace.signIn')}>
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
    </Modal>
  </>
}
