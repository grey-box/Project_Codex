import React, { type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Select, Input } from '../ui'
import type { LanguageOption } from '../../types/codex'

interface SearchBarProps {
  searchLanguage: string
  onSearchLanguageChange: (lang: string) => void
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  onSearch: () => void
  isLoading: boolean
  languages: LanguageOption[]
}

export const SearchBar: React.FC<SearchBarProps> = ({
  searchLanguage,
  onSearchLanguageChange,
  searchQuery,
  onSearchQueryChange,
  onSearch,
  isLoading,
  languages,
}) => {
  const { t } = useTranslation()

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch()
    }
  }

  const languageOptions = [
    { value: 'all', label: 'All languages' },
    ...languages.map((lang) => ({
      value: lang.code,
      label: `${lang.label} (${lang.code.toUpperCase()})`,
    })),
  ]

  return (
    <div className="w-full space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-3 items-end">
        {/* Language Filter */}
        <div className="w-full">
          <Select
            id="search-language"
            label="Search Language"
            value={searchLanguage}
            options={languageOptions}
            onChange={(e) => onSearchLanguageChange(e.target.value)}
          />
        </div>

        {/* Drug Input & Search Button */}
        <div className="sm:col-span-2 md:col-span-3 flex flex-col sm:flex-row gap-2 items-end">
          <div className="flex-1 w-full">
            <Input
              id="drug-search"
              label={t('home.searchTitle') || 'Drug Search'}
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('home.sourcePlaceholder') || 'Search RxNorm drug, brand or synonym...'}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              }
            />
          </div>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={onSearch}
            isLoading={isLoading}
            className="sm:w-auto w-full px-6 h-10.5 shrink-0"
          >
            {t('common.search') || 'Search'}
          </Button>
        </div>
      </div>
    </div>
  )
}
