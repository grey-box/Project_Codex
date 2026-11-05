import { API_BASE_URL } from './api'
import { getAuthHeaders } from './session'
import type { CsvRecord } from '../utils/csvConverter'

export const EXPORT_COLUMNS = {
  demo: ['generic_name', 'brand_name', 'country', 'original_language', 'translated_language'],
  rxnorm: ['conceptID', 'ds', 'name', 'rxcui', 'tty'],
} as const
export type ExportDataset = keyof typeof EXPORT_COLUMNS
export type ExportNameType = 'generic' | 'brand'

export async function getExportRecords(
  dataset: ExportDataset, nameType: ExportNameType, start: string, end: string, signal: AbortSignal,
): Promise<CsvRecord[]> {
  const query = new URLSearchParams({ source: dataset, name_type: nameType })
  if (start.trim()) query.set('start_name', start.trim())
  if (end.trim()) query.set('end_name', end.trim())
  const response = await fetch(`${API_BASE_URL}/csv?${query}`, { headers: getAuthHeaders(), signal })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Unable to export medications.')
  if (!Array.isArray(data?.csv) || data.csv.some((row: unknown) => !row || typeof row !== 'object' || Array.isArray(row))) {
    throw new Error('The server returned an invalid export response.')
  }
  return data.csv
}
