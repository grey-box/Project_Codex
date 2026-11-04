import React from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageFilterModal } from '../language/LanguageFilterModal'
import type { LanguageOption } from '../../types/codex'

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
