import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { Header } from './components/layout/Header'
import { SearchBar } from './components/search/SearchBar'
import { ResultsTable } from './components/results/ResultsTable'
import { TranslationPanel } from './components/translation/TranslationPanel'
import type { SearchResultRow, TranslateResultRow, LanguageOption } from './types/codex'
import { LANGUAGE_COUNTRY_MAP, FALLBACK_LANGUAGES } from './types/codex'
import { getLanguages, searchDrug, translateDrug } from './services/api'

function App() {
  const { t, i18n } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResultRow[]>([])
  const [selectedResult, setSelectedResult] = useState<SearchResultRow | null>(null)
  const [availableLanguages, setAvailableLanguages] = useState<string[]>(FALLBACK_LANGUAGES)
  const [searchLanguage, setSearchLanguage] = useState('all')
  const [targetLanguage, setTargetLanguage] = useState('es')
  const [targetCountry, setTargetCountry] = useState('MX')
  const [translatedName, setTranslatedName] = useState('')
  const [translatedBrand, setTranslatedBrand] = useState('')
  const [translateError, setTranslateError] = useState('')
  const [searchError, setSearchError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const [hasBrand, setHasBrand] = useState(false)

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
    setTranslatedName('')
    setTranslatedBrand('')
    setTranslateError('')
  }

  const loadLanguages = async (isActive: boolean) => {
    try {
      const nextLanguages = await getLanguages()
      if (!isActive) return
      setAvailableLanguages(nextLanguages)
      setTargetLanguage((current) => (nextLanguages.includes(current) ? current : nextLanguages[0]))
    } catch {
      if (!isActive) return
      setAvailableLanguages(FALLBACK_LANGUAGES)
      setTargetLanguage((current) => (FALLBACK_LANGUAGES.includes(current) ? current : FALLBACK_LANGUAGES[0]))
    }
  }

  useEffect(() => {
    let isActive = true
    loadLanguages(isActive)
    return () => {
      isActive = false
    }
  }, [])

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

    setIsLoading(true)
    setSearchError('')
    setTranslateError('')
    setSearchResults([])
    setSelectedResult(null)
    setTranslatedName('')
    setTranslatedBrand('')

    try {
      const data = await searchDrug(searchQuery)

      if (!data || !data.name) {
        setSearchResults([])
        setSearchError('No results found')
      } else {
        setHasBrand(Boolean(data.brand))
        setSearchResults([data])
        setSearchError('')
      }
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

    setIsTranslating(true)
    setTranslateError('')
    setTranslatedName('')
    setTranslatedBrand('')

    try {
      const payload = await translateDrug(selectedResult.name, targetLanguage, finalCountry)
      const results = payload.results ?? []
      const name = results.length > 0 ? extractTranslatedName(results) : '-'
      const brand = results.length > 0 ? extractTranslatedBrand(results) : '-'
      setTranslatedName(name)
      setTranslatedBrand(brand)
      if (results.length === 0 || name === '-') {
        setTranslateError('No translation found for the selected language')
      }
    } catch (err) {
      setTranslateError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setIsTranslating(false)
    }
  }

  const languages: LanguageOption[] = availableLanguages.map((code) => ({
    code,
    label: getLanguageLabel(code),
  }))

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      {/* Top Navigation */}
      <Header languages={languages} onImportSuccess={() => loadLanguages(true)} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 md:px-6 py-6 md:py-10 space-y-6 md:space-y-8">
        {/* Hero Section */}
        <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#1e4840] tracking-tight">
              {t('home.pageTitle') || 'Grey Box Pharma-Cross'}
            </h1>
            <p className="text-sm md:text-base text-slate-600 mt-1 max-w-2xl">
              {t('home.pageDescription') || 'Multilingual medical normalization and cross-border drug intelligence powered by RxNorm and Neo4j knowledge graph.'}
            </p>
          </div>
          <button
            type="button"
            className="self-start sm:self-auto px-3.5 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            {t('common.help') || 'Documentation'}
          </button>
        </section>

        {/* Search & Results Panel */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 md:p-8 space-y-6">
          <SearchBar
            searchLanguage={searchLanguage}
            onSearchLanguageChange={setSearchLanguage}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            onSearch={handleSearch}
            isLoading={isLoading}
            languages={languages}
          />

          <ResultsTable
            results={searchResults}
            selectedResult={selectedResult}
            onSelectResult={(result) => {
              setSelectedResult(result)
              setTranslatedName('')
              setTranslatedBrand('')
              setTranslateError('')
            }}
            hasBrand={hasBrand}
            searchError={searchError}
          />

          {selectedResult && (
            <TranslationPanel
              selectedResult={selectedResult}
              targetLanguage={targetLanguage}
              targetCountry={targetCountry}
              onTargetLanguageChange={handleLanguageChange}
              onTargetCountryChange={setTargetCountry}
              onTranslate={handleTranslateSelected}
              isTranslating={isTranslating}
              languages={languages}
              availableCountries={availableCountries}
              translatedName={translatedName}
              translatedBrand={translatedBrand}
              translateError={translateError}
            />
          )}
        </section>
      </main>
    </div>
  )
}

export default App
