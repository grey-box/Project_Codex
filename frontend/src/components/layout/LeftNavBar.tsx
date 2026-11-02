import React from 'react'
import { useTranslation } from 'react-i18next'
import { PopulateDropdown } from '../populate/PopulateDropdown'
import { ImportLanguageModal } from '../import/ImportLanguageModal'
import { OcrModal } from '../ocr/OcrModal'
import { AccountMenu } from './AccountMenu'
import { WorkspaceFooter } from './WorkspaceFooter'
import type { WorkspaceToolsProps } from './WorkspaceTools'

interface LeftNavBarProps extends WorkspaceToolsProps {
  onNavigate: () => void
  onCloseNavigation: () => void
}

export const LeftNavBar: React.FC<LeftNavBarProps> = ({ onImportSuccess, onSelectTerm, currentSearchLanguage, onNavigate, onCloseNavigation }) => {
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
          <p className="workspace-nav-label">{t('workspace.navigationSection')}</p>
          <a className="workspace-nav-active" href="#drug-search" aria-current="page" onClick={onNavigate}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="10.5" cy="10.5" r="7" /><path d="m16 16 5 5" /></svg>
            {t('workspace.medicationSearch')}
          </a>
          {onSelectTerm && <OcrModal fullWidth onSelectTerm={onSelectTerm} currentLanguage={currentSearchLanguage} triggerLabel={t('workspace.scanMedication')} />}
        </div>
        <div className="workspace-sidebar-group">
          <p className="workspace-nav-label">{t('workspace.manageData')}</p>
          <PopulateDropdown fullWidth triggerLabel={t('workspace.populateSources')} />
          <ImportLanguageModal fullWidth onImportSuccess={onImportSuccess} />
        </div>
      </nav>
      <AccountMenu />
      <WorkspaceFooter />
    </>
  )
}
