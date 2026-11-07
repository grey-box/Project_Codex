import type { SearchResultRow } from '../types/codex'

export type ResultSortOrder = 'original' | 'name-asc' | 'name-desc'

/** Sort the visible matches without changing the API order or selected records. */
export function sortMedicationResults(results: SearchResultRow[], order: ResultSortOrder, locale: string): SearchResultRow[] {
  if (order === 'original') return results
  const collator = new Intl.Collator(locale, { sensitivity: 'base', numeric: true })
  const direction = order === 'name-asc' ? 1 : -1
  return [...results].sort((left, right) => direction * collator.compare(left.name, right.name))
}
