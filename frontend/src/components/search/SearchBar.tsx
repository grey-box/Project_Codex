import React from 'react'
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

  const languageOptions = [
    { value: 'all', label: t('workspace.allLanguages') },
    ...languages.map((lang) => ({
      value: lang.code,
      label: `${lang.label} (${lang.code.toUpperCase()})`,
    })),
  ]

  return (
    <form className="workspace-search" onSubmit={(event) => {
      event.preventDefault()
      if (!isLoading) onSearch()
    }}>
      <Input id="drug-search" label={t('workspace.medicationName')} value={searchQuery}
        onChange={(event) => onSearchQueryChange(event.target.value)}
        placeholder={t('home.sourcePlaceholder')} autoComplete="off"
        icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="7" strokeWidth="1.5" /><path d="m16 16 5 5" strokeWidth="1.5" />
        </svg>} />
      <Select id="search-language" label={t('workspace.searchLanguage')} value={searchLanguage}
        options={languageOptions} onChange={(event) => onSearchLanguageChange(event.target.value)} />
      <Button type="submit" isLoading={isLoading} className="workspace-search-button">
        {isLoading ? t('workspace.searching') : t('common.search')}
      </Button>
    </form>
  )
}
