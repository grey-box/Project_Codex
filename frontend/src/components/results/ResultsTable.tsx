import React from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../ui'
import type { SearchResultRow } from '../../types/codex'

interface ResultsTableProps {
  results: SearchResultRow[]
  selectedResult: SearchResultRow | null
  onSelectResult: (result: SearchResultRow) => void
  hasBrand: boolean
  isLoading: boolean
  hasSearched: boolean
  query: string
  tools: React.ReactNode
  searchError?: string
  onRetry: () => void
}

export const ResultsTable: React.FC<ResultsTableProps> = ({
  results,
  selectedResult,
  onSelectResult,
  hasBrand,
  searchError,
  isLoading,
  hasSearched,
  query,
  tools,
  onRetry,
}) => {
  const { t } = useTranslation()

  const isRowSelected = (row: SearchResultRow) => {
    if (!selectedResult) return false
    return (
      selectedResult.name === row.name &&
      selectedResult.brand === row.brand &&
      selectedResult.language === row.language &&
      selectedResult.country === row.country &&
      selectedResult.source_id === row.source_id
    )
  }

  return (
    <section className="workspace-surface workspace-results" aria-busy={isLoading} aria-labelledby="results-title">
      <div className="workspace-results-heading">
        <div className="workspace-results-summary"><h2 id="results-title">
          {t('home.resultsTitle') || 'Search Results'}
        </h2>
        {results.length > 0 && (
          <>
            <span className="workspace-result-count" aria-label={t('workspace.matchCount', { count: results.length })}>{results.length}</span>
            <span className="workspace-result-query">{t('workspace.resultQuery', { query })}</span>
          </>
        )}
        </div>
        {selectedResult && <a href="#medication-details" className="workspace-details-link">{t('workspace.viewDetails')}</a>}
        {tools}
      </div>

      {isLoading ? (
        <div className="workspace-results-loading" role="status">
          <h3>{t('workspace.searching')}</h3>
          <div aria-hidden="true" className="workspace-skeleton-list">
            {[0, 1, 2, 3].map(row => <div className="workspace-skeleton-row" key={row}>
              <span /><span /><span />
            </div>)}
          </div>
        </div>
      ) : searchError ? (
        <div className="workspace-results-empty workspace-results-error">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v6m0 3h.01" /></svg>
          <h3>{t('workspace.searchFailed')}</h3>
          <p>{searchError}</p>
          <Button type="button" variant="secondary" onClick={onRetry}>{t('tools.tryAgain')}</Button>
        </div>
      ) : results.length > 0 ? (
        <>
          {/* Desktop & Tablet Table View */}
          <div className="workspace-result-table overflow-hidden bg-white">
            <div className="overflow-x-auto">
              <table data-has-brand={hasBrand} className="w-full text-left border-collapse text-xs md:text-sm">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-3 px-4">
                      {t('workspace.medicationName')}
                    </th>
                    {hasBrand && <th className="py-3 px-4">{t('workspace.brand')}</th>}
                    <th className="py-3 px-4">{t('workspace.type')}</th>
                    <th className="py-3 px-4">
                      {t('workspace.language')}
                    </th>
                    <th className="py-3 px-4">
                      {t('workspace.countries')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {results.map((row, index) => {
                    const selected = isRowSelected(row)
                    return (
                      <tr
                        key={`${row.name}-${row.brand}-${row.language}-${row.country ?? 'unknown'}-${row.source_id ?? index}`}
                        onClick={() => onSelectResult(row)}
                        className={`workspace-result-row ${selected ? 'is-selected' : ''}`}
                      >
                        <td className="workspace-result-name">
                          <button type="button" aria-pressed={selected} onClick={(event) => {
                            event.stopPropagation()
                            onSelectResult(row)
                          }} className="text-left underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-700 rounded-sm">{row.name}</button>
                        </td>
                        {hasBrand && <td className="py-3 px-4">{row.brand || '-'}</td>}
                        <td className="py-3 px-4">
                          <span className="text-slate-500">
                            {row.type || (hasBrand ? 'brand name drug' : 'ingredient')}
                          </span>
                        </td>
                        <td className="py-3 px-4 uppercase">{row.language}</td>
                        <td className="py-3 px-4">{row.country ?? '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Card View */}
          <div className="workspace-result-cards">
            {results.map((row, index) => {
              const selected = isRowSelected(row)
              return (
                <button
                  type="button"
                  aria-pressed={selected}
                  key={`card-${row.name}-${row.brand}-${row.language}-${row.country ?? 'unknown'}-${row.source_id ?? index}`}
                  onClick={() => onSelectResult(row)}
                  className={`workspace-result-card ${selected ? 'is-selected' : ''}`}
                >
                  <span className="flex items-start justify-between gap-2">
                    <span className="workspace-result-card-name">{row.name}</span>
                    <span className="workspace-result-language">
                      {row.language}
                    </span>
                  </span>

                  {row.brand && (
                    <span className="block text-xs text-slate-600 mt-1">
                      <span className="font-medium text-slate-500">{t('workspace.brand')}:</span> {row.brand}
                    </span>
                  )}

                  <span className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
                    <span>
                      {t('workspace.type')}: {row.type || (hasBrand ? 'brand name drug' : 'ingredient')}
                    </span>
                    <span>•</span>
                    <span>{t('workspace.countries')}: {row.country ?? 'N/A'}</span>
                  </span>
                </button>
              )
            })}
          </div>
        </>
      ) : (
        <div className="workspace-results-empty" role="status">
          <div className="workspace-search-symbol" aria-hidden="true">⌕</div>
          <h3>{t(isLoading ? 'workspace.searching' : searchError ? 'workspace.searchFailed' : hasSearched ? 'workspace.noMatches' : 'workspace.emptyTitle')}</h3>
          <p>{t(isLoading ? 'workspace.searchingDescription' : searchError ? 'workspace.retrySearch' : hasSearched ? 'workspace.noMatchesDescription' : 'workspace.emptyDescription')}</p>
        </div>
      )}
    </section>
  )
}
