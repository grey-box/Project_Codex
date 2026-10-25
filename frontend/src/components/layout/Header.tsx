import React from 'react'
import { useTranslation } from 'react-i18next'
import { PopulateDropdown } from '../populate/PopulateDropdown'
import { ImportLanguageModal } from '../import/ImportLanguageModal'
import { LanguageSelector } from '../language/LanguageSelector'
import { LanguageFilterModal } from '../language/LanguageFilterModal'
import { OcrModal } from '../ocr/OcrModal'
import type { LanguageOption } from '../../types/codex'
import { AccountMenu } from './AccountMenu'

export interface WorkspaceToolsProps {
  onImportSuccess?: () => void
  onSelectTerm?: (term: string) => void
  currentSearchLanguage?: string
  allLoadedLanguages?: LanguageOption[]
  selectedLanguages?: string[]
  onToggleLanguage?: (code: string) => void
  onSelectAllLanguages?: () => void
  onDeselectAllLanguages?: () => void
  onApplyLanguageFilter?: () => void
}

interface HeaderProps {
  languages: LanguageOption[]
  navigationOpen: boolean
  onToggleNavigation: () => void
  toggleRef: React.RefObject<HTMLButtonElement | null>
}

export const Header: React.FC<HeaderProps> = ({ languages, navigationOpen, onToggleNavigation, toggleRef }) => {
  const { t } = useTranslation()
  return (
    <header className="workspace-header">
      <div className="workspace-header-inner">
        <button type="button" ref={toggleRef} className="workspace-navigation-toggle"
          aria-label={t('workspace.openNavigation')} aria-controls="workspace-navigation"
          aria-expanded={navigationOpen} onClick={onToggleNavigation}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <nav aria-label={t('workspace.breadcrumb')} className="workspace-breadcrumb">
          <a href="#main-content">Medical Codex</a>
          <span aria-hidden="true">/</span>
          <span aria-current="page">{t('workspace.medications')}</span>
        </nav>
        <LanguageSelector languages={languages} />
      </div>
    </header>
  )
}

interface SidebarProps extends WorkspaceToolsProps {
  onNavigate: () => void
  onCloseNavigation: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ onImportSuccess, onSelectTerm, currentSearchLanguage, onNavigate, onCloseNavigation }) => {
  const { t } = useTranslation()
  return (
    <>
      <div className="workspace-sidebar-heading">
        <a href="#drug-search" className="workspace-brand" aria-label="Medical Codex" onClick={onNavigate}>
          <span className="workspace-wordmark" aria-hidden="true">codex</span>
        </a>
        <button type="button" className="workspace-navigation-close" onClick={onCloseNavigation}
          aria-label={t('workspace.closeNavigation')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" /></svg>
        </button>
      </div>
      <nav className="workspace-sidebar-navigation" aria-label={t('workspace.tools')}>
        <div className="workspace-sidebar-group">
          <p className="workspace-nav-label">{t('workspace.eyebrow')}</p>
          <a className="workspace-nav-active" href="#drug-search" aria-current="page" onClick={onNavigate}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="10.5" cy="10.5" r="7" /><path d="m16 16 5 5" /></svg>
            {t('workspace.medications')}
          </a>
          {onSelectTerm && <OcrModal onSelectTerm={onSelectTerm} currentLanguage={currentSearchLanguage} />}
        </div>
        <div className="workspace-sidebar-group">
          <p className="workspace-nav-label">{t('workspace.manageData')}</p>
          <PopulateDropdown />
          <ImportLanguageModal onImportSuccess={onImportSuccess} />
        </div>
      </nav>
      <AccountMenu />
    </>
  )
}

export const WorkspaceTools: React.FC<WorkspaceToolsProps> = ({
  allLoadedLanguages, selectedLanguages, onToggleLanguage,
  onSelectAllLanguages, onDeselectAllLanguages, onApplyLanguageFilter,
}) => {
  const { t } = useTranslation()
  return (
    <div className="workspace-tools" role="group" aria-label={t('workspace.tools')}>
      <div className="workspace-tool-group">
        {allLoadedLanguages && selectedLanguages && onToggleLanguage && onSelectAllLanguages && onDeselectAllLanguages && onApplyLanguageFilter && (
          <LanguageFilterModal allLanguages={allLoadedLanguages} selectedLanguages={selectedLanguages}
            onToggleLanguage={onToggleLanguage} onSelectAll={onSelectAllLanguages}
            onDeselectAll={onDeselectAllLanguages} onApply={onApplyLanguageFilter} />
        )}
      </div>
    </div>
  )
}
