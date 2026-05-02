import './App.css'
import { useTranslation } from 'react-i18next'
import { useEffect, useState, type KeyboardEvent } from 'react'

interface LanguagesResponse {
  languages: string[]
}

interface SearchResultRow {
  source_id: string | null
  source_name: string | null
  name: string
  type: string
  country: string | null
  language: string
  uploaded_at: string | null
}

interface SearchResponse {
  query: string
  count: number
  results: SearchResultRow[]
}

interface TranslateResultRow {
  source_id: string | null
  source_name: string | null
  name: string
  type: string
  country: string | null
  language: string
  uploaded_at: string | null
}

interface TranslateResponse {
  found: boolean
  results: TranslateResultRow[]
}

const API_BASE_URL = 'http://localhost:8000'
const FALLBACK_LANGUAGES = ['en', 'es', 'fr', 'de']

function App() {
  const { t, i18n } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResultRow[]>([])
  const [selectedResult, setSelectedResult] = useState<SearchResultRow | null>(null)
  const [availableLanguages, setAvailableLanguages] = useState<string[]>(FALLBACK_LANGUAGES)
  const [searchLanguage, setSearchLanguage] = useState('all')
  const [targetLanguage, setTargetLanguage] = useState('es')
  const [translatedName, setTranslatedName] = useState('')
  const [translateError, setTranslateError] = useState('')
  const [searchError, setSearchError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const [exportLanguage, setExportLanguage] = useState<string>(availableLanguages[0])
  const [exportError, setExportError] = useState('')
  const [isExporting, setIsExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState('')

  const getLanguageLabel = (code: string) => {
    const raw = code.trim()
    const normalized = raw.toLowerCase()

    // Backend may return either ISO codes (en) or full names (English).
    if (normalized.length > 3) {
      return raw
    }

    try {
      const displayNames = new Intl.DisplayNames([i18n.language], { type: 'language' })
      return displayNames.of(normalized) ?? normalized.toUpperCase()
    } catch {
      return normalized.toUpperCase()
    }
  }

  useEffect(() => {
    let isActive = true

    const loadLanguages = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/languages`)
        if (!response.ok) {
          throw new Error('Failed to load languages')
        }

        const data = (await response.json()) as LanguagesResponse
        const nextLanguages = Array.isArray(data.languages) && data.languages.length > 0 ? data.languages : FALLBACK_LANGUAGES
        if (!isActive) {
          return
        }

        setAvailableLanguages(nextLanguages)
        setTargetLanguage((current) => (nextLanguages.includes(current) ? current : nextLanguages[0]))
        setExportLanguage((current) => (nextLanguages.includes(current) ? current : nextLanguages[0]))
      } catch {
        if (!isActive) {
          return
        }

        setAvailableLanguages(FALLBACK_LANGUAGES)
        setTargetLanguage((current) => (FALLBACK_LANGUAGES.includes(current) ? current : FALLBACK_LANGUAGES[0]))
      }
    }

    void loadLanguages()

    return () => {
      isActive = false
    }
  }, [])

  const extractTranslatedName = (rows: TranslateResultRow[]) => {
    const names = rows
      .map((row) => row.name)
      .filter((name): name is string => Boolean(name && name.trim()))

    if (names.length === 0) {
      return '-'
    }

    return Array.from(new Set(names)).join(', ')
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

    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 20,
        }),
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null)
        throw new Error(errorBody?.detail ?? 'Failed to search')
      }

      const data = (await response.json()) as SearchResponse
      const rows = Array.isArray(data.results) ? data.results : []
      const filteredRows =
        searchLanguage === 'all'
          ? rows
          : rows.filter((row) => row.language.toLowerCase() === searchLanguage.toLowerCase())

      setSearchResults(filteredRows)

      if (filteredRows.length === 0) {
        setSearchError('No results found')
      }
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'An error occurred during search')
      setSearchResults([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      void handleSearch()
    }
  }

  const handleTranslateSelected = async () => {
    if (!selectedResult) {
      setTranslateError('Select a search result first')
      return
    }

    setIsTranslating(true)
    setTranslateError('')
    setTranslatedName('')

    try {
      const response = await fetch(`${API_BASE_URL}/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          term: selectedResult.name,
          source_lang: selectedResult.language,
          target_lang: targetLanguage,
        }),
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null)
        throw new Error(errorBody?.detail ?? 'Translation request failed')
      }

      const payload = (await response.json()) as TranslateResponse
      const name = payload.found ? extractTranslatedName(payload.results ?? []) : '-'
      setTranslatedName(name)
      if (!payload.found || name === '-') {
        setTranslateError('No translation found for the selected language')
      }
    } catch (err) {
      setTranslateError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setIsTranslating(false)
    }
  }

  const rowsToCsv = (rows: any[]) => {
    if (!rows || rows.length === 0) return ''
    const headerOrder = ['concept_id', 'source_id', 'source_name', 'name', 'type', 'country', 'language', 'uploaded_at']
    const keys = Array.from(new Set([...headerOrder, ...Object.keys(rows[0] || {})]))
    const escapeVal = (v: any) => {
      if (v === null || v === undefined) return ''
      const s = String(v)
      if (s.includes('"') || s.includes(',') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`
      }
      return s
    }
    const lines = [keys.join(',')]
    rows.forEach((r) => {
      lines.push(keys.map((k) => escapeVal((r as any)[k])).join(','))
    })
    return lines.join('\n')
  }

  const downloadBlob = (filename: string, text: string) => {
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const fetchAndDownload = async (urlSuffix: string, filename: string) => {
    setIsExporting(true)
    setExportError('')
    setExportMessage('')
    try {
      const res = await fetch(`${API_BASE_URL}${urlSuffix}`)
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? 'Export failed')
      }
      const data = await res.json()
      const rows = Array.isArray(data.rows) ? data.rows : data.results ?? []
      const csv = rowsToCsv(rows)
      if (!csv) throw new Error('No rows to export')
      downloadBlob(filename, csv)
      setExportMessage(`Downloaded ${rows.length} rows`)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }
  const downloadByLanguage = () => {
    if (!exportLanguage.trim()) {
      setExportError('Choose a language')
      return
    }
    fetchAndDownload(`/csv/language/${encodeURIComponent(exportLanguage.trim())}`, `codex_language_${exportLanguage.trim()}.csv`)
  }

  const languages = availableLanguages.map((code) => ({ code, label: getLanguageLabel(code) }))

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
          <div className="search-surface">
            <div className="search-grid">
              <div className="field-stack">
                <label htmlFor="search-language">Search language</label>
                <select
                  id="search-language"
                  value={searchLanguage}
                  onChange={(event) => setSearchLanguage(event.target.value)}
                >
                  <option value="all">All languages</option>
                  {languages.map((lang) => (
                    <option key={`search-${lang.code}`} value={lang.code}>
                      {lang.label} ({lang.code.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
              <div className="search-row" style={{ gridColumn: '1 / -1' }}>
                <input
                  id="drug-search"
                  placeholder={t('home.sourcePlaceholder')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyPress}
                />
                <button type="button" onClick={handleSearch} disabled={isLoading}>
                  {isLoading ? 'Searching...' : t('common.search')}
                </button>
              </div>
            </div>

            <div className="results-block">
              <h3>{t('home.resultsTitle')}</h3>
              {searchError && <div className="message message--error">{searchError}</div>}
              {translateError && <div className="message message--error">{translateError}</div>}
              {isTranslating && <div className="message message--info">Translating selected result...</div>}
              {searchResults.length > 0 ? (
                <div className="results-table-wrap">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Drug Name</th>
                        <th>Type</th>
                        <th>Language</th>
                        <th>Country</th>
                      </tr>
                    </thead>
                    <tbody>
                      {searchResults.map((row, index) => (
                        <tr
                          key={`${row.name}-${row.language}-${row.country ?? 'unknown'}-${row.source_id ?? index}`}
                          className={
                            selectedResult &&
                            selectedResult.name === row.name &&
                            selectedResult.language === row.language &&
                            selectedResult.country === row.country &&
                            selectedResult.source_id === row.source_id
                              ? 'row-selected'
                              : ''
                          }
                          onClick={() => {
                            setSelectedResult(row)
                            setTranslatedName('')
                            setTranslateError('')
                          }}
                          style={{ cursor: 'pointer' }}
                        >
                          <td>{row.name}</td>
                          <td>{row.type}</td>
                          <td>{row.language}</td>
                          <td>{row.country ?? '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : searchQuery && !isLoading ? (
                <div className="message message--muted">No results found</div>
              ) : (
                <button type="button" className="results-select">
                  <span>{t('home.sampleMedicine')}</span>
                  <span aria-hidden="true">▾</span>
                </button>
              )}

              {selectedResult && (
                <div style={{ marginTop: '14px' }}>
                  <div className="search-grid">
                    <div className="field-stack">
                      <label htmlFor="target-language">Translate selected into</label>
                      <select
                        id="target-language"
                        value={targetLanguage}
                        onChange={(event) => setTargetLanguage(event.target.value)}
                      >
                        {languages.map((lang) => (
                          <option key={lang.code} value={lang.code}>
                            {lang.label} ({lang.code.toUpperCase()})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="search-row">
                      <button type="button" onClick={handleTranslateSelected} disabled={isTranslating}>
                        {isTranslating ? 'Translating...' : 'Translate Selected'}
                      </button>
                    </div>
                  </div>

                  <div className="results-table-wrap" style={{ marginTop: '10px' }}>
                    <table className="results-table">
                      <thead>
                        <tr>
                          <th>Original Drug Name (Language)</th>
                          <th>Drug Name in {targetLanguage.toUpperCase()}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>{selectedResult.name} ({selectedResult.language})</td>
                          <td>{translatedName || '-'}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="tool-panel" style={{ marginTop: 20 }}>
          <h2>Export CSV</h2>
          <div className="search-surface">
            <div className="search-grid">
              <div className="field-stack">
                <label htmlFor="export-language">Language</label>
                <select id="export-language" value={exportLanguage} onChange={(e) => setExportLanguage(e.target.value)}>
                  {availableLanguages.map((l) => (
                    <option key={l} value={l}>
                      {getLanguageLabel(l)} ({l})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field-stack" style={{ alignSelf: 'end' }}>
                <button type="button" className="translate-btn" onClick={downloadByLanguage} disabled={isExporting}>{isExporting ? 'Downloading...' : 'Download CSV'}</button>
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              {isExporting && <div className="message message--info">Preparing CSV...</div>}
              {exportError && <div className="message message--error">{exportError}</div>}
              {exportMessage && <div className="message message--success">{exportMessage}</div>}
            </div>
          </div>
        </section>

      </main>
    </div>
  )
}

export default App