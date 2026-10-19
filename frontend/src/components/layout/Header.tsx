import React from 'react'
import { useTranslation } from 'react-i18next'
import { PopulateDropdown } from '../populate/PopulateDropdown'
import { ImportLanguageModal } from '../import/ImportLanguageModal'
import { LanguageSelector } from '../language/LanguageSelector'
import { LanguageFilterModal } from '../language/LanguageFilterModal'
import { OcrModal } from '../ocr/OcrModal'
import type { LanguageOption } from '../../types/codex'

export interface WorkspaceToolsProps {
  languages: LanguageOption[]
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

export const Header: React.FC = () => {
  const { t } = useTranslation()
  return (
    <header className="workspace-header">
      <div className="workspace-header-inner">
        <a href="#main-content" className="workspace-brand">GREY-BOX</a>
        <span className="workspace-product">Medical Codex</span>
        <a className="workspace-docs" href="https://github.com/grey-box/Project_Codex#readme" target="_blank" rel="noreferrer">
          {t('workspace.documentation')} <span aria-hidden="true">↗</span>
        </a>
      </div>
    </header>
  )
}

export const WorkspaceTools: React.FC<WorkspaceToolsProps> = ({
  languages, onImportSuccess, onSelectTerm, currentSearchLanguage,
  allLoadedLanguages, selectedLanguages, onToggleLanguage,
  onSelectAllLanguages, onDeselectAllLanguages, onApplyLanguageFilter,
}) => {
  const { t } = useTranslation()
  return (
    <div className="workspace-tools" role="group" aria-label={t('workspace.tools')}>
      <div className="workspace-tool-group">
        <PopulateDropdown />
        <ImportLanguageModal onImportSuccess={onImportSuccess} />
        {onSelectTerm && <OcrModal onSelectTerm={onSelectTerm} currentLanguage={currentSearchLanguage} />}
      </div>
      <div className="workspace-tool-group">
        {allLoadedLanguages && selectedLanguages && onToggleLanguage && onSelectAllLanguages && onDeselectAllLanguages && onApplyLanguageFilter && (
          <LanguageFilterModal allLanguages={allLoadedLanguages} selectedLanguages={selectedLanguages}
            onToggleLanguage={onToggleLanguage} onSelectAll={onSelectAllLanguages}
            onDeselectAll={onDeselectAllLanguages} onApply={onApplyLanguageFilter} />
        )}
        <LanguageSelector languages={allLoadedLanguages ?? languages} />
      </div>
    </div>
  )
}
