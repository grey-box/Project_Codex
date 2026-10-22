import type {
  LanguagesResponse,
  SearchResponse,
  TranslateResponse,
} from '../types/codex'
import { FALLBACK_LANGUAGES } from '../types/codex'
import { getAuthHeaders, setAccessToken } from './session'

export const API_BASE_URL = 'http://localhost:8000'

// Matches the team's ACL branch contract; the backend must expose /api/login.
export async function loginUser(email: string, password: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Sign-in is unavailable on this backend.')
  if (typeof data?.access_token !== 'string' || !data.access_token.trim()) throw new Error('The server did not return an access token.')
  setAccessToken(data.access_token)
}

/**
 * Fetches available language codes that have data in Neo4j.
 */
export async function getLanguages(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/languages`, { headers: getAuthHeaders() })
    if (!response.ok) {
      throw new Error('Failed to load languages')
    }
    const data = (await response.json()) as LanguagesResponse
    return Array.isArray(data.languages) && data.languages.length > 0
      ? data.languages
      : FALLBACK_LANGUAGES
  } catch (error) {
    console.warn('Using fallback languages due to error:', error)
    return FALLBACK_LANGUAGES
  }
}

/**
 * Searches for a drug / medical term in Neo4j.
 */
export async function searchDrug(query: string): Promise<SearchResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/search?term=${encodeURIComponent(query.toLowerCase())}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        query: query,
        limit: 20,
      }),
    }
  )

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    throw new Error(errorBody?.detail ?? 'Failed to search')
  }

  const data = await response.json()
  if (Array.isArray(data)) {
    return data as SearchResponse[]
  }
  return data ? [data as SearchResponse] : []
}

/**
 * Translates a drug term to a destination language and country.
 */
export async function translateDrug(
  term: string,
  lang: string,
  country: string
): Promise<TranslateResponse> {
  const response = await fetch(`${API_BASE_URL}/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      term,
      lang,
      country,
    }),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    throw new Error(errorBody?.detail ?? 'Translation request failed')
  }

  return (await response.json()) as TranslateResponse
}

/**
 * Scans an image file using OCR and extracts medical terms with fuzzy matching.
 */
export async function scanOcrImage(file: File, sourceLanguage?: string, signal?: AbortSignal): Promise<import('../types/codex').OcrResultItem[]> {
  const formData = new FormData()
  formData.append('file', file)
  if (sourceLanguage && sourceLanguage !== 'all') {
    formData.append('source_language', sourceLanguage)
  }

  const response = await fetch(`${API_BASE_URL}/ocrmatching/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    signal,
  })

  if (!response.ok) {
    const errData = await response.json().catch(() => null)
    throw new Error(errData?.detail || 'OCR extraction failed')
  }

  const data = await response.json()
  if (Array.isArray(data)) {
    return data
  } else if (data && Array.isArray(data.results)) {
    return data.results
  }
  return []
}
