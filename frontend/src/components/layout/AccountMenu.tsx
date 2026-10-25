import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Documentation } from './Documentation'
import { SignIn } from './SignIn'
import { Dropdown } from '../ui'
import { setAccessToken } from '../../services/session'

type Theme = 'light' | 'dark'

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem('codex-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* Storage can be unavailable in private or embedded contexts. */ }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function AccountMenu() {
  const { t } = useTranslation()
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [email, setEmail] = useState('')
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('codex-theme', theme) } catch { /* The switch still works without persistence. */ }
  }, [theme])
  return (
    <div className="workspace-account">
      <Dropdown align="left" widthClass="w-[200px]" className="w-full" trigger={open => (
        <button type="button" className="workspace-account-trigger" aria-expanded={open} aria-label={t('workspace.account')}>
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1" aria-hidden="true"><circle cx="14" cy="14" r="13" /><circle cx="14" cy="11" r="3" /><path d="M8 22v-2a6 6 0 0 1 12 0v2" /></svg>
          <span>{email || t('workspace.account')}</span><span aria-hidden="true">⌃</span>
        </button>
      )}>
        {email ? <button className="workspace-account-action" type="button" onClick={() => { setAccessToken(''); setEmail('') }}>{t('workspace.signOut')}</button> : <SignIn onSuccess={setEmail} />}
        <Documentation />
        <div className="workspace-appearance">
          <p>{t('workspace.appearance')}</p>
          <div className="workspace-mode-options">
            {(['light', 'dark'] as const).map(mode => <button key={mode} type="button" aria-pressed={theme === mode} onClick={() => setTheme(mode)}>{t(`workspace.${mode}`)}</button>)}
          </div>
        </div>
      </Dropdown>
    </div>
  )
}
