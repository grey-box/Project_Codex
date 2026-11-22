
import { API_BASE_URL } from './api'
import { getAuthHeaders } from './session'
import type { CsvRecord } from '../utils/csvConverter'

export type ExportReportType = 'medication' | 'clinical'
export type ExportNameType = 'generic' | 'brand'

export async function getExportRecords(
  reportType: ExportReportType,
  nameType: ExportNameType,
  start: string,
  end: string,
  signal: AbortSignal,
): Promise<CsvRecord[]> {
  const query = new URLSearchParams()

  if (reportType === 'medication') {
    query.set('name_type', nameType)
  }

  if (start.trim()) {
    query.set('start_name', start.trim())
  }

  if (end.trim()) {
    query.set('end_name', end.trim())
  }

  const endpoint = reportType === 'medication'
    ? '/api/medication-export'
    : '/api/clinical-export'

  const response = await fetch(
    `${API_BASE_URL}${endpoint}?${query.toString()}`,
    {
      headers: getAuthHeaders(),
      signal,
    },
  )

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Unable to retrieve export records.',
    )
  }

  if (
    !Array.isArray(data?.csv) ||
    data.csv.some(
      (row: unknown) =>
        !row || typeof row !== 'object' || Array.isArray(row),
    )
  ) {
    throw new Error('The server returned an invalid export response.')
  }

  return data.csv as CsvRecord[]
}