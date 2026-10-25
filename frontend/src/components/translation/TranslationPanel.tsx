import React from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Select, Alert } from '../ui'
import type { SearchResultRow, LanguageOption, CountryOption } from '../../types/codex'

interface TranslationPanelProps {
  selectedResult: SearchResultRow
  targetLanguage: string
  targetCountry: string
  onTargetLanguageChange: (lang: string) => void
  onTargetCountryChange: (country: string) => void
  onTranslate: () => void
  isTranslating: boolean
  languages: LanguageOption[]
  availableCountries: CountryOption[]
  translatedName: string
  translatedBrand: string
  translateError?: string
}

export const TranslationPanel: React.FC<TranslationPanelProps> = ({
  selectedResult,
  targetLanguage,
  targetCountry,
  onTargetLanguageChange,
  onTargetCountryChange,
  onTranslate,
  isTranslating,
  languages,
  availableCountries,
  translatedName,
  translatedBrand,
  translateError,
}) => {
  const { t } = useTranslation()

  const languageOptions = languages.map((lang) => ({
    value: lang.code,
    label: `${lang.label} (${lang.code.toUpperCase()})`,
  }))

  const countryOptions =
    availableCountries.length > 0
      ? availableCountries.map((c) => ({
          value: c.code,
          label: `${c.label} (${c.code.toUpperCase()})`,
        }))
      : [{ value: '', label: t('home.noCountries') || 'No countries available' }]

  return (
    <div className="workspace-details">
      <h2 className="workspace-eyebrow">{t('workspace.medicationDetails')}</h2>
      <div className="workspace-selected">
        <h3>{selectedResult.name}</h3>
        {selectedResult.brand && <p>{selectedResult.brand}</p>}
      </div>
      <dl className="workspace-medication-facts">
        <div><dt>{t('workspace.type')}</dt><dd>{selectedResult.type || '—'}</dd></div>
        <div><dt>{t('workspace.language')}</dt><dd>{languages.find(language => language.code.toLowerCase() === selectedResult.language.toLowerCase())?.label || selectedResult.language.toUpperCase()}</dd></div>
        <div><dt>{t('workspace.countries')}</dt><dd>{selectedResult.country || '—'}</dd></div>
      </dl>
      <div className="workspace-translate-controls">
        <h2>{t('workspace.translateTitle')}</h2>
        <Select id="target-language" label={t('home.targetLanguage')} value={targetLanguage}
          options={languageOptions} disabled={isTranslating} onChange={(event) => onTargetLanguageChange(event.target.value)} />
        <Select id="target-country" label={t('home.targetCountry')} value={targetCountry}
          options={countryOptions} disabled={isTranslating || availableCountries.length === 0}
          onChange={(event) => onTargetCountryChange(event.target.value)} />
        <Button type="button" onClick={onTranslate} isLoading={isTranslating} fullWidth className="min-h-10">
          {t('common.translate')}
        </Button>
      </div>
      {translateError && <div><Alert type="error" message={translateError} /></div>}
      <div aria-live="polite" aria-busy={isTranslating}>
        {isTranslating ? <p className="text-sm text-slate-500">{t('workspace.translating')}</p> : translatedName && !translateError ? (
          <dl className="workspace-translation-output">
            <div className="workspace-translation-caption"><dt>{t('home.translation')}</dt><dd>{targetLanguage.toUpperCase()} · {targetCountry.toUpperCase()}</dd></div>
            <div className="workspace-translated-term"><dt className="sr-only">{t('home.translation')}</dt><dd>{translatedName}</dd></div>
            <div className="workspace-translated-brand"><dt>{t('workspace.regionalBrand')}</dt><dd>{translatedBrand || '—'}</dd></div>
          </dl>
        ) : !translateError && <p className="text-sm text-slate-500">{t('workspace.destinationHint')}</p>}
      </div>
    </div>
  )
}
