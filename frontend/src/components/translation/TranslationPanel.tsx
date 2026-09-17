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
    <div className="w-full mt-6 pt-6 border-t border-slate-200 space-y-4">
      <div className="flex items-center gap-2">
        <span className="p-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-base">🌐</span>
        <div>
          <h4 className="text-sm font-bold text-slate-800">
            {t('home.localizeTitle') || 'Translate & Cross-Reference Drug'}
          </h4>
          <p className="text-xs text-slate-500">
            {t('home.selectedDrug') || 'Selected drug:'} <strong className="text-slate-700">{selectedResult.name}</strong> ({selectedResult.language.toUpperCase()})
          </p>
        </div>
      </div>

      {/* Target Language & Country selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-3 items-end">
        {/* Target Language */}
        <div className="w-full">
          <Select
            id="target-language"
            label={t('home.targetLanguage') || 'Target Language'}
            value={targetLanguage}
            options={languageOptions}
            onChange={(e) => onTargetLanguageChange(e.target.value)}
          />
        </div>

        {/* Target Country */}
        <div className="w-full">
          <Select
            id="target-country"
            label={t('home.targetCountry') || 'Target Country'}
            value={targetCountry}
            options={countryOptions}
            disabled={availableCountries.length === 0}
            onChange={(e) => onTargetCountryChange(e.target.value)}
          />
        </div>

        {/* Translate Action */}
        <div className="sm:col-span-1 md:col-span-2">
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={onTranslate}
            isLoading={isTranslating}
            className="w-full sm:w-auto px-6 h-10.5"
          >
            {t('common.translate') || 'Translate Selected'}
          </Button>
        </div>
      </div>

      {/* Error / Info State */}
      {translateError && <Alert type="error" message={translateError} />}

      {/* Translation Result Card */}
      {(translatedName || isTranslating) && (
        <div className="mt-4 overflow-hidden rounded-xl border border-emerald-200 bg-emerald-50/30 p-4 md:p-5">
          <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-800 mb-3">
            {t('home.crossReferencedMatch') || 'Cross-Referenced Match'}
          </h5>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
                {t('home.original') || 'Original'} ({selectedResult.language.toUpperCase()})
              </div>
              <div className="text-sm font-bold text-slate-900 mt-1">
                {selectedResult.name}
              </div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
                {t('home.translation') || 'Translation'} ({targetLanguage.toUpperCase()})
              </div>
              <div className="text-sm font-bold text-emerald-700 mt-1">
                {translatedName || (isTranslating ? '...' : '-')}
              </div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
                {t('home.brandInCountry') || 'Brand in'} {targetCountry.toUpperCase()}
              </div>
              <div className="text-sm font-bold text-slate-800 mt-1">
                {translatedBrand || (isTranslating ? '...' : '-')}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
