import { useTranslation } from 'react-i18next'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Header, Sidebar, WorkspaceTools } from './components/layout/Header'
import { SearchBar } from './components/search/SearchBar'
import { ResultsTable } from './components/results/ResultsTable'
import { TranslationPanel } from './components/translation/TranslationPanel'
import type { SearchResultRow, TranslateResultRow, LanguageOption } from './types/codex'
import { LANGUAGE_COUNTRY_MAP, FALLBACK_LANGUAGES } from './types/codex'
import { getLanguages, searchDrug, translateDrug } from './services/api'

function App() {
  const { t, i18n } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [unfilteredResults, setSearchResults] = useState<SearchResultRow[]>([])
  const [selectedResult, setSelectedResult] = useState<SearchResultRow | null>(null)
  const [loadedLanguages, setLoadedLanguages] = useState<string[]>(FALLBACK_LANGUAGES)
  const [availableLanguages, setAvailableLanguages] = useState<string[]>(FALLBACK_LANGUAGES)
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(FALLBACK_LANGUAGES)
  const [searchLanguage, setSearchLanguage] = useState('all')
  const [targetLanguage, setTargetLanguage] = useState('es')
  const [targetCountry, setTargetCountry] = useState('MX')
  const [translatedName, setTranslatedName] = useState('')
  const [translatedBrand, setTranslatedBrand] = useState('')
  const [translateError, setTranslateError] = useState('')
  const [searchError, setSearchError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const translationRequest = useRef(0)

  const clearTranslation = () => {
    translationRequest.current += 1
    setIsTranslating(false)
    setTranslatedName('')
    setTranslatedBrand('')
    setTranslateError('')
  }

  const getLanguageLabel = (code: string) => {
    const raw = code.trim()
    const normalized = raw.toLowerCase()

    let label = raw
    if (normalized.length <= 3) {
      try {
        const displayNames = new Intl.DisplayNames([i18n.language], { type: 'language' })
        label = displayNames.of(normalized) ?? normalized.toUpperCase()
      } catch {
        label = normalized.toUpperCase()
      }
    }
    return label.charAt(0).toUpperCase() + label.slice(1)
  }

  const availableCountries = LANGUAGE_COUNTRY_MAP[targetLanguage] ?? []

  const getFirstCountryForLanguage = (langCode: string): string => {
    const available = LANGUAGE_COUNTRY_MAP[langCode] ?? []
    return available.length > 0 ? available[0].code : ''
  }

  const handleLanguageChange = (newLang: string) => {
    const newCountry = getFirstCountryForLanguage(newLang)
    setTargetLanguage(newLang)
    setTargetCountry(newCountry)
    clearTranslation()
  }

  const loadLanguages = useCallback(async (isActive: () => boolean) => {
    try {
      const nextLanguages = await getLanguages()
      if (!isActive()) return
      setLoadedLanguages(nextLanguages)
      setAvailableLanguages(nextLanguages)
      setSelectedLanguages(nextLanguages)
      setTargetLanguage((current) => (nextLanguages.includes(current) ? current : nextLanguages[0]))
    } catch {
      if (!isActive()) return
      setLoadedLanguages(FALLBACK_LANGUAGES)
      setAvailableLanguages(FALLBACK_LANGUAGES)
      setSelectedLanguages(FALLBACK_LANGUAGES)
      setTargetLanguage((current) => (FALLBACK_LANGUAGES.includes(current) ? current : FALLBACK_LANGUAGES[0]))
    }
  }, [])

  useEffect(() => {
    let isActive = true
    loadLanguages(() => isActive)
    return () => {
      isActive = false
    }
  }, [loadLanguages])

  const hasActiveLanguageMatch = (
    itemLanguageString: string | null | undefined,
    activeLanguages: string[],
    selectedSearchLanguage: string = 'all'
  ): boolean => {
    if (!itemLanguageString) {
      return false
    }

    const activeNormalized = activeLanguages.map((l) => l.toLowerCase().trim())
    const itemLangs = itemLanguageString
      .split(',')
      .map((lang) => lang.trim().toLowerCase())

    const matchesActiveLanguages = itemLangs.some((lang) =>
      activeNormalized.includes(lang)
    )

    if (!matchesActiveLanguages) {
      return false
    }

    const searchLangNormalized = selectedSearchLanguage.toLowerCase().trim()
    if (searchLangNormalized !== 'all') {
      return itemLangs.includes(searchLangNormalized)
    }

    return true
  }

  const handleCheckboxToggle = (code: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  const handleSelectAll = () => {
    setSelectedLanguages([...loadedLanguages])
  }

  const handleDeselectAll = () => {
    setSelectedLanguages([])
  }

  const handleApplyLanguageFilter = () => {
    const filtered = loadedLanguages.filter((code) => selectedLanguages.includes(code))
    setAvailableLanguages(filtered)
    if (!filtered.includes(targetLanguage) && filtered.length > 0) {
      handleLanguageChange(filtered[0])
    }

    if (selectedResult && !hasActiveLanguageMatch(selectedResult.language, filtered, searchLanguage)) {
      setSelectedResult(null)
      clearTranslation()
    }
  }

  const handleResetLanguages = () => {
    setSelectedLanguages([...loadedLanguages])
    setAvailableLanguages([...loadedLanguages])
    setSearchLanguage('all')
  }

  const searchResults = unfilteredResults.filter((item) =>
    hasActiveLanguageMatch(item.language, availableLanguages, searchLanguage)
  )
  const hasBrand = searchResults.some((item) => Boolean(item.brand))

  const extractTranslatedName = (rows: TranslateResultRow[]) => {
    const names = rows
      .map((row) => row.translation)
      .filter((name): name is string => Boolean(name && name.trim()))

    if (names.length === 0) return '-'
    return Array.from(new Set(names)).join(', ')
  }

  const extractTranslatedBrand = (rows: TranslateResultRow[]) => {
    const brands = rows
      .map((row) => row.brand)
      .filter((brand): brand is string => Boolean(brand && brand.trim()))

    if (brands.length === 0) return '-'
    return Array.from(new Set(brands)).join(', ')
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchError('Please enter a search term')
      return
    }

    clearTranslation()
    setHasSearched(true)
    setIsLoading(true)
    setSearchError('')
    setTranslateError('')
    setSearchResults([])
    setSelectedResult(null)
    setTranslatedName('')
    setTranslatedBrand('')

    try {
      const data = await searchDrug(searchQuery)
      setSearchResults(data)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'An error occurred during search')
      setSearchResults([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleTranslateSelected = async () => {
    if (!selectedResult) {
      setTranslateError('Select a search result first')
      return
    }

    const validCountries = (LANGUAGE_COUNTRY_MAP[targetLanguage] ?? []).map((c) => c.code)
    const finalCountry = validCountries.includes(targetCountry)
      ? targetCountry
      : getFirstCountryForLanguage(targetLanguage)

    const requestId = ++translationRequest.current
    setIsTranslating(true)
    setTranslateError('')
    setTranslatedName('')
    setTranslatedBrand('')

    try {
      const payload = await translateDrug(selectedResult.name, targetLanguage, finalCountry)
      if (requestId !== translationRequest.current) return
      const results = payload.results ?? []
      const name = results.length > 0 ? extractTranslatedName(results) : '-'
      const brand = results.length > 0 ? extractTranslatedBrand(results) : '-'
      setTranslatedName(name)
      setTranslatedBrand(brand)
      if (results.length === 0 || name === '-') {
        setTranslateError('No translation found for the selected language')
      }
    } catch (err) {
      if (requestId === translationRequest.current) {
        setTranslateError(err instanceof Error ? err.message : 'Translation failed')
      }
    } finally {
      if (requestId === translationRequest.current) setIsTranslating(false)
    }
  }

  const languages: LanguageOption[] = availableLanguages.map((code) => ({
    code,
    label: getLanguageLabel(code),
  }))

  const allLoadedLanguages: LanguageOption[] = loadedLanguages.map((code) => ({
    code,
    label: getLanguageLabel(code),
  }))

  return (
    <div className="workspace-shell">
      <a className="skip-link" href="#main-content">{t('workspace.skipToSearch')}</a>
      <Sidebar onImportSuccess={() => loadLanguages(() => true)}
        onSelectTerm={setSearchQuery} currentSearchLanguage={searchLanguage} />
      <div className="workspace-content">
        <Header languages={allLoadedLanguages} />
        <main id="main-content" className="workspace-main">
          <section className="workspace-intro" aria-labelledby="workspace-title">
            <div>
              <h1 id="workspace-title">{t('workspace.medications')}</h1>
            </div>
          </section>
          <section className="workspace-surface workspace-search-surface" aria-label={t('home.searchTitle')}>
            <SearchBar searchLanguage={searchLanguage} onSearchLanguageChange={(language) => {
              setSearchLanguage(language)
              setSelectedResult(null)
              clearTranslation()
            }} searchQuery={searchQuery} onSearchQueryChange={setSearchQuery}
              onSearch={handleSearch} isLoading={isLoading} languages={languages} />
            <WorkspaceTools
              allLoadedLanguages={allLoadedLanguages}
              selectedLanguages={selectedLanguages}
              onToggleLanguage={handleCheckboxToggle}
              onSelectAllLanguages={handleSelectAll}
              onDeselectAllLanguages={handleDeselectAll}
              onApplyLanguageFilter={handleApplyLanguageFilter}
            />
            {availableLanguages.length < loadedLanguages.length && (
              <div className="workspace-filter-notice">
                <span>{t('workspace.activeLanguages', { languages: availableLanguages.map(l => l.toUpperCase()).join(', ') || '—' })}</span>
                <button type="button" onClick={handleResetLanguages}>{t('workspace.resetLanguages')}</button>
              </div>
            )}
          </section>
          <div className="workspace-results-layout">
            <ResultsTable results={searchResults} selectedResult={selectedResult}
              onSelectResult={(result) => {
                setSelectedResult(result)
                clearTranslation()
              }} hasBrand={hasBrand} searchError={searchError} isLoading={isLoading} hasSearched={hasSearched} />
            <aside className="workspace-surface workspace-translation" aria-label={t('workspace.translateTitle')}>
              {selectedResult ? (
                <TranslationPanel selectedResult={selectedResult} targetLanguage={targetLanguage}
                  targetCountry={targetCountry} onTargetLanguageChange={handleLanguageChange}
                  onTargetCountryChange={(country) => {
                    setTargetCountry(country)
                    clearTranslation()
                  }} onTranslate={handleTranslateSelected} isTranslating={isTranslating}
                  languages={languages} availableCountries={availableCountries}
                  translatedName={translatedName} translatedBrand={translatedBrand} translateError={translateError} />
              ) : (
                <div className="workspace-translation-empty">
                  <p className="workspace-eyebrow">{t('workspace.stepThree')}</p>
                  <h2>{t('workspace.translateTitle')}</h2>
                  <div className="workspace-empty-icon" aria-hidden="true">Aa <span>↔</span> 文</div>
                  <h3>{t('workspace.selectTitle')}</h3>
                  <p>{t('workspace.selectDescription')}</p>
                </div>
              )}
            </aside>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
