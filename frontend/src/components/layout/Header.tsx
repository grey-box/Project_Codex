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

export const Header: React.FC<{ languages: LanguageOption[] }> = ({ languages }) => {
  const { t } = useTranslation()
  return (
    <header className="workspace-header">
      <div className="workspace-header-inner">
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

export const Sidebar: React.FC<WorkspaceToolsProps> = ({ onImportSuccess, onSelectTerm, currentSearchLanguage }) => {
  const { t } = useTranslation()
  return (
    <nav className="workspace-sidebar" aria-label={t('workspace.tools')}>
      <a href="#main-content" className="workspace-brand" aria-label="Medical Codex">
        <span className="workspace-wordmark" aria-hidden="true">codex</span>
      </a>
      <div className="workspace-sidebar-group">
        <p className="workspace-nav-label">{t('workspace.eyebrow')}</p>
        <a className="workspace-nav-active" href="#main-content" aria-current="page">
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
      <AccountMenu />
    </nav>
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
