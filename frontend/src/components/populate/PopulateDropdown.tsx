import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Dropdown } from '../ui'

const API_BASE_URL = 'http://localhost:8000'

interface SourceOption {
  id: string
  label: string
  description: string
}

const SOURCES: SourceOption[] = [
  { id: 'drugbank', label: 'DrugBank', description: 'Pharmaceutical & commercial brand database' },
  { id: 'snomed', label: 'SNOMED CT', description: 'Global clinical terminology & diagnoses' },
  { id: 'rxnorm', label: 'RxNorm', description: 'Standardized clinical drugs (US NLM)' },
  { id: 'icd11', label: 'ICD-11', description: 'WHO International Classification of Diseases' },
]

interface PopulateDropdownProps {
  fullWidth?: boolean
}

export const PopulateDropdown: React.FC<PopulateDropdownProps> = ({ fullWidth = false }) => {
  const { t } = useTranslation()
  const [selectedSources, setSelectedSources] = useState<Record<string, boolean>>({
    drugbank: false,
    snomed: false,
    rxnorm: false,
    icd11: false,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<string>('')

  const toggleSource = (id: string) => {
    setSelectedSources((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const selectedCount = Object.values(selectedSources).filter(Boolean).length

  const handlePopulateClick = async () => {
    const sourcesToPopulate = Object.entries(selectedSources)
      .filter(([, isSelected]) => isSelected)
      .map(([id]) => id)

    if (sourcesToPopulate.length === 0) return

    setIsLoading(true)
    setProgress('Starting population...')

    try {
      const response = await fetch(`${API_BASE_URL}/api/populate-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedSources: sourcesToPopulate }),
      })

      if (!response.body) return

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue

          try {
            const cleanLine = trimmed.startsWith('data:') ? trimmed.replace(/^data:\s*/, '') : trimmed
            const parsed = JSON.parse(cleanLine)
            if (parsed.progress) {
              setProgress(parsed.progress)
            }
          } catch (err) {
            console.error('Error parsing chunk:', err)
          }
        }
      }
      setProgress('Successfully populated Neo4j!')
    } catch (error) {
      console.error('Error during streaming:', error)
      setProgress('Error processing request.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dropdown
      widthClass="w-72 sm:w-80"
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
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
          }
        >
          <span>{t('sides.populateButton') || 'Populate'}</span>
          {selectedCount > 0 && (
            <span className="bg-emerald-400 text-slate-900 text-xs font-bold px-1.5 py-0.5 rounded-full">
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
          <span>🧬</span> {t('sides.populateLabel') || 'Populate local source(s):'}
        </h4>
        <span className="text-xs text-slate-400 font-medium">Neo4j</span>
      </div>

      {/* Sources Checkboxes */}
      <div className="space-y-2 mb-4">
        {SOURCES.map((source) => (
          <label
            key={source.id}
            className={`flex items-start gap-3 p-2 rounded-lg cursor-pointer transition-colors border ${
              selectedSources[source.id]
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-slate-50 hover:bg-slate-100 border-transparent'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedSources[source.id]}
              onChange={() => toggleSource(source.id)}
              className="mt-0.5 w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 cursor-pointer"
            />
            <div className="flex-1 text-xs">
              <div className="font-semibold text-slate-800">{source.label}</div>
              <div className="text-slate-500">{source.description}</div>
            </div>
          </label>
        ))}
      </div>

      {/* Progress / Status Message */}
      {progress && (
        <div className="mb-3 p-2 bg-slate-100 rounded-md text-xs text-slate-700 font-medium wrap-break-word text-center">
          {progress}
        </div>
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
