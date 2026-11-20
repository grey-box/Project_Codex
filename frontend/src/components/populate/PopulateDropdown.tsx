import React, { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Dropdown } from '../ui'
import { API_BASE_URL } from '../../services/api'
import { readPopulationResponse } from '../../services/population'
import { getAuthHeaders } from '../../services/session'

interface SourceOption {
  id: string
  label: string
  description: string
}

const SOURCES: SourceOption[] = [
  { id: 'drugbank', label: 'DrugBank', description: 'tools.drugbank' },
  { id: 'snomed', label: 'SNOMED CT', description: 'tools.snomed' },
  { id: 'rxnorm', label: 'RxNorm', description: 'tools.rxnorm' },
  { id: 'icd11', label: 'ICD-11', description: 'tools.icd11' },
]

interface PopulateDropdownProps {
  fullWidth?: boolean
  triggerLabel?: string
}

export const PopulateDropdown: React.FC<PopulateDropdownProps> = ({ fullWidth = false, triggerLabel }) => {
  const { t } = useTranslation()
  const [selectedSources, setSelectedSources] = useState<Record<string, boolean>>({
    drugbank: false,
    snomed: false,
    rxnorm: false,
    icd11: false,
  })
  const [drugbankAPIKey, setDrugbankAPIKey] = useState('')
  const [icdID, setIcdID] = useState('')
  const [icdSecret, setIcdSecret] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<string>('')
  const [populationError, setPopulationError] = useState('')
  const [invalidCredentials, setInvalidCredentials] = useState<string[]>([])
  const populationPending = useRef(false)

  const clearFeedback = () => {
    setProgress('')
    setPopulationError('')
    setInvalidCredentials([])
  }

  const toggleSource = (id: string) => {
    setSelectedSources((prev) => ({ ...prev, [id]: !prev[id] }))
    clearFeedback()
  }

  const selectedCount = Object.values(selectedSources).filter(Boolean).length

  const handlePopulateClick = async () => {
    if (populationPending.current) return
    const sourcesToPopulate = Object.entries(selectedSources)
      .filter(([, isSelected]) => isSelected)
      .map(([id]) => id)

    if (sourcesToPopulate.length === 0) return

    clearFeedback()
    const missing = [
      ...(selectedSources.drugbank && !drugbankAPIKey.trim() ? ['drugbank-key'] : []),
      ...(selectedSources.icd11 && !icdID.trim() ? ['icd-id'] : []),
      ...(selectedSources.icd11 && !icdSecret.trim() ? ['icd-secret'] : []),
    ]
    if (missing.length) {
      setInvalidCredentials(missing)
      setPopulationError(t('tools.populationCredentialsRequired'))
      document.getElementById(missing[0])?.focus()
      return
    }

    populationPending.current = true
    setIsLoading(true)
    setPopulationError('')
    setProgress(t('tools.populationStarting'))

    try {
      const response = await fetch(`${API_BASE_URL}/api/populate-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          selectedSources: sourcesToPopulate,
          DBAPIKey: selectedSources.drugbank ? drugbankAPIKey : '',
          ICDID: selectedSources.icd11 ? icdID : '',
          ICDSecret: selectedSources.icd11 ? icdSecret : '',
        }),
      })

      await readPopulationResponse(response, setProgress)
      setProgress(t('tools.populationSuccess'))
    } catch (error) {
      setProgress('')
      setPopulationError(error instanceof Error ? error.message : t('tools.populationFailed'))
    } finally {
      populationPending.current = false
      setIsLoading(false)
    }
  }

  return (
    <Dropdown
      widthClass="w-80 sm:w-96"
      align="right"
      className={fullWidth ? 'w-full' : ''}
      trigger={(isOpen) => (
        <Button
          type="button"
          variant="nav"
          size="md"
          fullWidth={fullWidth}
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <ellipse cx="12" cy="5" rx="9" ry="3" strokeWidth="1.5" />
              <path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0" strokeWidth="1.5" />
            </svg>
          }
        >
          <span>{triggerLabel || t('sides.populateButton') || 'Populate'}</span>
          {selectedCount > 0 && (
            <span className="workspace-source-count">
              {selectedCount}
            </span>
          )}
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </Button>
      )}
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
        <h4 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          {t('sides.populateLabel') || 'Populate local source(s):'}
        </h4>
        <span className="text-xs text-slate-400 font-medium">Neo4j</span>
      </div>

      {/* Sources Checkboxes */}
      <div className="space-y-2 mb-4">
        {SOURCES.map((source) => (
          <label
            key={source.id}
            className={`workspace-source-option flex items-start gap-3 p-2 rounded-lg cursor-pointer transition-colors border ${
              selectedSources[source.id]
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-slate-50 hover:bg-slate-100 border-transparent'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedSources[source.id]}
              disabled={isLoading}
              onChange={() => toggleSource(source.id)}
              className="mt-0.5 w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 cursor-pointer"
            />
            <div className="flex-1 text-xs">
              <div className="font-semibold text-slate-800">{source.label}</div>
              <div className="text-slate-500">{t(source.description)}</div>
            </div>
          </label>
        ))}
      </div>

      {/* API Keys Configuration Section */}
      {(selectedSources.drugbank || selectedSources.icd11) && <div className="pt-3 border-t border-slate-100 mb-4 space-y-2.5">
        <div className="text-xs font-semibold text-slate-700">
          {t('sides.keyLabel') || 'API Keys & Credentials:'}
        </div>

        {/* DrugBank Key */}
        {selectedSources.drugbank && <div>
          <label htmlFor="drugbank-key" className="block text-[11px] font-medium text-slate-600 mb-1">
            {t('sides.drugbankAPIKey') || 'DrugBank API Key'}
          </label>
          <input
            id="drugbank-key"
            type="password"
            value={drugbankAPIKey}
            disabled={isLoading}
            required
            aria-invalid={invalidCredentials.includes('drugbank-key') || undefined}
            aria-describedby={invalidCredentials.includes('drugbank-key') ? 'population-credential-error' : undefined}
            onChange={(e) => { setDrugbankAPIKey(e.target.value); clearFeedback() }}
            placeholder={t('sides.drugbankAPIKey') || 'DrugBank API Key'}
            className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white"
          />
        </div>}

        {/* ICD-11 Credentials */}
        {selectedSources.icd11 && <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div>
            <label htmlFor="icd-id" className="block text-[11px] font-medium text-slate-600 mb-1">
              {t('sides.icdID') || 'ICD-11 ID'}
            </label>
            <input
              id="icd-id"
              type="text"
              value={icdID}
              disabled={isLoading}
              required
              aria-invalid={invalidCredentials.includes('icd-id') || undefined}
              aria-describedby={invalidCredentials.includes('icd-id') ? 'population-credential-error' : undefined}
              onChange={(e) => { setIcdID(e.target.value); clearFeedback() }}
              placeholder={t('tools.clientId')}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white"
            />
          </div>
          <div>
            <label htmlFor="icd-secret" className="block text-[11px] font-medium text-slate-600 mb-1">
              {t('sides.icdSecret') || 'ICD-11 Secret'}
            </label>
            <input
              id="icd-secret"
              type="password"
              value={icdSecret}
              disabled={isLoading}
              required
              aria-invalid={invalidCredentials.includes('icd-secret') || undefined}
              aria-describedby={invalidCredentials.includes('icd-secret') ? 'population-credential-error' : undefined}
              onChange={(e) => { setIcdSecret(e.target.value); clearFeedback() }}
              placeholder={t('tools.clientSecret')}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white"
            />
          </div>
        </div>}
        {invalidCredentials.length > 0 && <p id="population-credential-error" className="sr-only">{t('tools.populationCredentialsRequired')}</p>}
      </div>}

      {/* Progress / Status Message */}
      {progress && (
        <div role="status" aria-live="polite" className="mb-3 p-2 bg-slate-100 rounded-md text-xs text-slate-700 font-medium wrap-break-word text-center">
          {progress}
        </div>
      )}
      {populationError && (
        <Alert type="error" message={populationError} />
      )}

      {/* Action Button */}
      <Button
        type="button"
        variant="primary"
        size="md"
        className="w-full text-xs"
        onClick={handlePopulateClick}
        disabled={isLoading || selectedCount === 0}
        isLoading={isLoading}
      >
        {t('sides.populateButton') || 'Populate'} ({selectedCount})
      </Button>
    </Dropdown>
  )
}
