import React from 'react'
import { useTranslation } from 'react-i18next'
import { Alert } from '../ui'
import type { SearchResultRow } from '../../types/codex'

interface ResultsTableProps {
  results: SearchResultRow[]
  selectedResult: SearchResultRow | null
  onSelectResult: (result: SearchResultRow) => void
  hasBrand: boolean
  isLoading: boolean
  hasSearched: boolean
  searchError?: string
}

export const ResultsTable: React.FC<ResultsTableProps> = ({
  results,
  selectedResult,
  onSelectResult,
  hasBrand,
  searchError,
  isLoading,
  hasSearched,
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
        <div><h2 id="results-title" className="text-sm font-medium">
          {t('home.resultsTitle') || 'Search Results'}
        </h2></div>
        {results.length > 0 && (
          <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-md">
            {t('workspace.matchCount', { count: results.length })}
          </span>
        )}
      </div>

      {searchError && <div className="px-6 pb-4"><Alert type="error" message={searchError} /></div>}

      {results.length > 0 ? (
        <>
          {/* Desktop & Tablet Table View */}
          <div className="hidden sm:block overflow-hidden border-t border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs md:text-sm">
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
                        className={`cursor-pointer transition-colors ${
                          selected
                            ? 'bg-emerald-50/80 font-medium text-emerald-950 hover:bg-emerald-100/60'
                            : 'hover:bg-slate-50/80 text-slate-700'
                        }`}
                      >
                        <td className="py-4 px-5 font-medium text-slate-900 flex items-center gap-2">
                          {selected && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
                          )}
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
          <div className="sm:hidden space-y-2.5 p-4">
            {results.map((row, index) => {
              const selected = isRowSelected(row)
              return (
                <button
                  type="button"
                  aria-pressed={selected}
                  key={`card-${row.name}-${row.brand}-${row.language}-${row.country ?? 'unknown'}-${row.source_id ?? index}`}
                  onClick={() => onSelectResult(row)}
                  className={`w-full text-left p-4 rounded-xl border transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-emerald-700 ${
                    selected
                      ? 'border-emerald-500 bg-emerald-50/50 shadow-xs ring-1 ring-emerald-500'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <span className="flex items-start justify-between gap-2">
                    <span className="block font-bold text-slate-900 text-sm">{row.name}</span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
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
