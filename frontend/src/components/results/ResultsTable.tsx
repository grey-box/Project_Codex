import React from 'react'
import { useTranslation } from 'react-i18next'
import { Alert } from '../ui'
import type { SearchResultRow } from '../../types/codex'

interface ResultsTableProps {
  results: SearchResultRow[]
  selectedResult: SearchResultRow | null
  onSelectResult: (result: SearchResultRow) => void
  hasBrand: boolean
  searchError?: string
}

export const ResultsTable: React.FC<ResultsTableProps> = ({
  results,
  selectedResult,
  onSelectResult,
  hasBrand,
  searchError,
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
    <div className="w-full space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
          {t('home.resultsTitle') || 'Search Results'}
        </h3>
        {results.length > 0 && (
          <span className="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
            {results.length} {results.length === 1 ? 'match' : 'matches'}
          </span>
        )}
      </div>

      {searchError && <Alert type="error" message={searchError} />}

      {results.length > 0 ? (
        <>
          {/* Desktop & Tablet Table View */}
          <div className="hidden sm:block overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs md:text-sm">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-3 px-4">
                      {hasBrand ? 'Drug Name for Brand' : 'Drug Name'}
                    </th>
                    {hasBrand && <th className="py-3 px-4">Brand</th>}
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">
                      {hasBrand ? 'Language for Brand' : 'Language'}
                    </th>
                    <th className="py-3 px-4">
                      {hasBrand ? 'Countries for Brand' : 'Countries'}
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
                        <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                          {selected && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
                          )}
                          <span>{row.name}</span>
                        </td>
                        {hasBrand && <td className="py-3 px-4">{row.brand || '-'}</td>}
                        <td className="py-3 px-4">
                          <span className="inline-block px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-600">
                            {hasBrand ? 'brand name drug' : row.type || 'ingredient'}
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
          <div className="sm:hidden space-y-2.5">
            {results.map((row, index) => {
              const selected = isRowSelected(row)
              return (
                <div
                  key={`card-${row.name}-${row.brand}-${row.language}-${row.country ?? 'unknown'}-${row.source_id ?? index}`}
                  onClick={() => onSelectResult(row)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    selected
                      ? 'border-emerald-500 bg-emerald-50/50 shadow-xs ring-1 ring-emerald-500'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-bold text-slate-900 text-sm">{row.name}</div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      {row.language}
                    </span>
                  </div>

                  {row.brand && (
                    <div className="text-xs text-slate-600 mt-1">
                      <span className="font-medium text-slate-500">Brand:</span> {row.brand}
                    </div>
                  )}

                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
                    <span>
                      Type: {hasBrand ? 'brand name drug' : row.type || 'ingredient'}
                    </span>
                    <span>•</span>
                    <span>Country: {row.country ?? 'N/A'}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      ) : (
        <div className="p-8 border border-dashed border-slate-200 rounded-xl bg-slate-50/50 text-center">
          <p className="text-sm font-medium text-slate-500">
            {t('home.sampleMedicine') || 'Search for a drug or click search to view matching results.'}
          </p>
        </div>
      )}
    </div>
  )
}
