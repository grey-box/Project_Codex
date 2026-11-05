import React from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageSelector } from '../language/LanguageSelector'
import type { LanguageOption } from '../../types/codex'

interface HeaderProps {
  languages: LanguageOption[]
  navigationOpen: boolean
  isMobile: boolean
  onToggleNavigation: () => void
  toggleRef: React.RefObject<HTMLButtonElement | null>
}

export const Header: React.FC<HeaderProps> = ({ languages, navigationOpen, isMobile, onToggleNavigation, toggleRef }) => {
  const { t } = useTranslation()
  const toggleLabel = t(isMobile ? 'workspace.openNavigation' : navigationOpen ? 'workspace.collapseSidebar' : 'workspace.expandSidebar')
  return (
    <header className="workspace-header">
      <div className="workspace-header-inner">
        <button type="button" ref={toggleRef}
          className="workspace-navigation-toggle order-last flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-md border border-[var(--workspace-line)] bg-[var(--workspace-surface)] text-[var(--workspace-ink)] hover:bg-[var(--workspace-active)] md:order-first md:size-9 md:border-0 md:bg-transparent md:text-[var(--workspace-muted)] md:hover:text-[var(--workspace-ink)]"
          aria-label={toggleLabel} title={toggleLabel} aria-controls="workspace-navigation"
          aria-expanded={navigationOpen} onClick={onToggleNavigation}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            {isMobile ? <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" /> : <>
              <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" />
              <path d={navigationOpen ? 'm16 9-3 3 3 3' : 'm13 9 3 3-3 3'} />
            </>}
          </svg>
        </button>
        <nav aria-label={t('workspace.breadcrumb')} className="workspace-breadcrumb">
          <span aria-current="page">{t('workspace.medications')}</span>
        </nav>
        <LanguageSelector languages={languages} />
      </div>
    </header>
  )
}
