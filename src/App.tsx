import './App.css'
import { useTranslation } from 'react-i18next'
import { useState, type KeyboardEvent } from 'react'

interface Drug {
  canonical_name: string
  source: string
  source_id: string
  is_poc: boolean
}

interface DrugName {
  name: string
  country: string
  language: string
  name_type: string
  is_primary: boolean
}

const API_BASE_URL = 'http://localhost:8000'

function App() {
  const { t, i18n } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Drug[]>([])
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null)
  const [sourceCountry, setSourceCountry] = useState('US')
  const [targetCountry, setTargetCountry] = useState('IN')
  const [translatedName, setTranslatedName] = useState('')
  const [translateError, setTranslateError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const [error, setError] = useState('')

  const countryOptions = [
    { code: 'US', label: 'English (US)' },
    { code: 'GB', label: 'English (UK)' },
    { code: 'IN', label: 'India' },
    { code: 'ES', label: 'Spain' },
    { code: 'FR', label: 'France' },
    { code: 'DE', label: 'Germany' },
  ]

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search term')
      return
    }

    setIsLoading(true)
    setError('')
    setSearchResults([])
    setSelectedDrug(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/drugs/search?q=${encodeURIComponent(searchQuery)}&limit=50`
      )
      if (!response.ok) {
        throw new Error('Failed to search drugs')
      }
      const data = await response.json()
      setSearchResults(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during search')
      setSearchResults([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleTranslate = async () => {
    if (!selectedDrug) {
      setTranslateError('Select a drug result first')
      setTranslatedName('')
      return
    }

    setIsTranslating(true)
    setTranslateError('')
    setTranslatedName('')

    try {
      const namesResponse = await fetch(
        `${API_BASE_URL}/drugs/${encodeURIComponent(selectedDrug.source)}/${encodeURIComponent(selectedDrug.source_id)}/names`
      )
      if (!namesResponse.ok) {
        throw new Error('Could not fetch names for selected drug')
      }

      const namesData = (await namesResponse.json()) as DrugName[]
      const sourceName =
        namesData.find((n) => n.country === sourceCountry && n.is_primary) ||
        namesData.find((n) => n.country === sourceCountry) ||
        namesData[0]

      if (!sourceName?.name) {
        throw new Error('No usable source name found for selected drug')
      }

      const translateResponse = await fetch(
        `${API_BASE_URL}/translate?name=${encodeURIComponent(sourceName.name)}&from_country=${encodeURIComponent(sourceCountry)}&to_country=${encodeURIComponent(targetCountry)}`
      )

      if (!translateResponse.ok) {
        if (translateResponse.status === 404) {
          throw new Error('No translation found for the selected countries')
        }
        throw new Error('Translation request failed')
      }

      const translation = await translateResponse.json()
      setTranslatedName(translation.translated_name || '')
    } catch (err) {
      setTranslateError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setIsTranslating(false)
    }
  }

  const languages = [
    { code: 'en', label: 'English' },
    { code: 'es', label: 'Spanish' },
    { code: 'fr', label: 'French' },
    { code: 'de', label: 'German' },
  ]

  return (
    <div className="page-shell">
      <header className="top-nav" aria-label="Main navigation">
        <div className="top-nav__left">
          <a href="#" className="brand" aria-label="Grey Box home">
            GREY-BOX
          </a>

          <nav className="main-links">
            <a href="#">{t('nav.home')}</a>
            <a href="#">{t('nav.about')}</a>
          </nav>
        </div>

        <div className="top-nav__right">
          <select
            aria-label="Select interface language"
            value={i18n.language}
            onChange={(event) => i18n.changeLanguage(event.target.value)}
          >
            {languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>

          <button type="button" className="icon-btn" aria-label="Open regions">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm8 10c0 1.07-.22 2.09-.61 3h-3.13a15.3 15.3 0 00.17-3 15.3 15.3 0 00-.17-3h3.13c.39.91.61 1.93.61 3zM12 20c-1.03-1.11-1.81-2.29-2.36-3.5h4.72c-.55 1.21-1.33 2.39-2.36 3.5zM9.11 15A13.3 13.3 0 018.8 12c0-1.04.11-2.04.31-3h5.78c.2.96.31 1.96.31 3 0 1.04-.11 2.04-.31 3H9.11zM4.61 15A7.97 7.97 0 014 12c0-1.07.22-2.09.61-3h3.13a15.3 15.3 0 00-.17 3c0 1.02.06 2.02.17 3H4.61zm1.01 1.5h2.43c.34.84.75 1.66 1.23 2.44a8.05 8.05 0 01-3.66-2.44zM8.05 7.5H5.62a8.05 8.05 0 013.66-2.44 14.1 14.1 0 00-1.23 2.44zm5.95-2.44a8.05 8.05 0 013.66 2.44h-2.43A14.1 14.1 0 0014 5.06zm1.95 13.88c.48-.78.89-1.6 1.23-2.44h2.43a8.05 8.05 0 01-3.66 2.44z" />
            </svg>
          </button>

          <button type="button" className="icon-btn" aria-label="Open X profile">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M18.9 2h3.2l-7 8 8.2 12h-6.4L12 15l-6.2 7H2.5l7.5-8.4L2.1 2h6.5l4.4 6.3L18.9 2zm-1.1 18h1.8L7.6 4H5.7l12.1 16z" />
            </svg>
          </button>

          <button type="button" className="icon-btn" aria-label="Open Facebook profile">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M13.5 21v-8h2.7l.4-3h-3.1V8.1c0-.9.3-1.6 1.7-1.6h1.5V3.8c-.3 0-1.2-.1-2.2-.1-2.2 0-3.8 1.3-3.8 3.8V10H8v3h2.7v8h2.8z" />
            </svg>
          </button>

          <button type="button" className="icon-btn" aria-label="Open LinkedIn profile">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6.4 8.7a1.7 1.7 0 110-3.4 1.7 1.7 0 010 3.4zM8 20H4.8V10H8v10zm12 0h-3.2v-5.4c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9V20H9.7V10h3.1v1.4h.1c.4-.8 1.5-1.8 3.1-1.8 3.3 0 3.9 2.2 3.9 5V20z" />
            </svg>
          </button>
        </div>
      </header>

      <main className="content">
        <section className="hero-row">
          <div>
            <h1>{t('home.pageTitle')}</h1>
            <p>{t('home.pageDescription')}</p>
          </div>
          <button type="button" className="help-btn">
            {t('common.help')}
          </button>
        </section>

        <section className="tool-panel">
          <h2>{t('home.searchTitle')}</h2>
          <div className="search-grid">
            <div className="field-stack">
              <label htmlFor="source-lang">{t('home.sourceLanguage')}</label>
              <select
                id="source-lang"
                value={sourceCountry}
                onChange={(event) => setSourceCountry(event.target.value)}
              >
                {countryOptions.map((country) => (
                  <option key={country.code} value={country.code}>
                    {country.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="search-row">
              <input 
                id="drug-search" 
                placeholder={t('home.sourcePlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
              />
              <button type="button" onClick={handleSearch} disabled={isLoading}>
                {isLoading ? 'Searching...' : t('common.search')}
              </button>
            </div>
          </div>

          <div className="results-block">
            <h3>{t('home.resultsTitle')}</h3>
            {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
            {searchResults.length > 0 ? (
              <>
                <button type="button" className="results-select">
                  <span>
                    {selectedDrug
                      ? selectedDrug.canonical_name
                      : `${searchResults.length} result${searchResults.length !== 1 ? 's' : ''} found`}
                  </span>
                  <span aria-hidden="true">▾</span>
                </button>
                <div style={{ marginTop: '10px', maxHeight: '200px', overflowY: 'auto' }}>
                  {searchResults.map((drug, idx) => (
                    <div
                      key={idx}
                      onClick={() => {
                        setSelectedDrug(drug)
                        setTranslatedName('')
                        setTranslateError('')
                      }}
                      style={{
                        padding: '8px',
                        borderBottom: '1px solid #e0e0e0',
                        cursor: 'pointer',
                        backgroundColor: selectedDrug === drug ? '#f0f0f0' : 'transparent',
                      }}
                    >
                      <strong>{drug.canonical_name}</strong>
                      <div style={{ fontSize: '0.85em', color: '#666' }}>
                        {drug.source} / {drug.source_id}
                      </div>
                    </div>
                  ))}
                </div>
                {selectedDrug && (
                  <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
                    <p><strong>{selectedDrug.canonical_name}</strong></p>
                    <p style={{ fontSize: '0.9em', color: '#666' }}>
                      Source: {selectedDrug.source} ({selectedDrug.source_id})
                    </p>
                  </div>
                )}
              </>
            ) : searchQuery && !isLoading ? (
              <div style={{ color: '#999' }}>No results found</div>
            ) : (
              <button type="button" className="results-select">
                <span>{t('home.sampleMedicine')}</span>
                <span aria-hidden="true">▾</span>
              </button>
            )}
          </div>
        </section>

        <section className="tool-panel">
          <h2>{t('home.localizeTitle')}</h2>
          <div className="translate-grid">
            <div className="field-stack">
              <label htmlFor="target-lang">{t('home.targetLanguage')}</label>
              <select
                id="target-lang"
                value={targetCountry}
                onChange={(event) => setTargetCountry(event.target.value)}
              >
                {countryOptions.map((country) => (
                  <option key={country.code} value={country.code}>
                    {country.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="translate-btn"
              onClick={handleTranslate}
              disabled={isTranslating || !selectedDrug}
            >
              {isTranslating ? 'Translating...' : t('common.translate')}
            </button>
            <input
              value={translatedName}
              readOnly
              placeholder={t('home.translationPlaceholder')}
              aria-label="Translation output"
            />
          </div>
          {translateError && <div style={{ color: 'red', marginTop: '8px' }}>{translateError}</div>}
        </section>
      </main>
    </div>
  )
}

export default App
