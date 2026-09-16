import type {
  LanguagesResponse,
  SearchResponse,
  TranslateResponse,
} from '../types/codex'
import { FALLBACK_LANGUAGES } from '../types/codex'

export const API_BASE_URL = 'http://localhost:8000'

/**
 * Fetches available language codes that have data in Neo4j.
 */
export async function getLanguages(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/languages`)
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
export async function searchDrug(query: string): Promise<SearchResponse | null> {
  const response = await fetch(
    `${API_BASE_URL}/search?term=${encodeURIComponent(query.toLowerCase())}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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

  const data = (await response.json()) as SearchResponse | null
  return data
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
