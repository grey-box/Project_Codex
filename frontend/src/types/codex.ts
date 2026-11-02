export interface CountryOption {
  code: string
  label: string
}

export interface LanguageOption {
  code: string
  label: string
}

export interface LanguagesResponse {
  languages: string[]
  countries?: Record<string, CountryOption[]>
}

export interface SearchResultRow {
  source_id: string | null
  source_name: string | null
  name: string
  brand: string | null
  type: string
  country: string
  language: string
  uploaded_at: string | null
}

export interface SearchResponse {
  source_id: string
  source_name: string
  name: string
  brand: string
  type: string
  country: string
  language: string
  uploaded_at: string
}

export interface TranslateResultRow {
  source_id: string | null
  source_name: string | null
  translation: string
  brand: string | null
  type: string
  country: string | null
  language: string
  uploaded_at: string | null
}

export interface TranslateResponse {
  found: boolean
  results: TranslateResultRow[]
}

export interface TranslateRequest {
  term: string
  lang: string
  country: string
}

// Dynamic countries loaded from Neo4j via /languages
export const LANGUAGE_COUNTRY_MAP: Record<string, CountryOption[]> = {}

export const FALLBACK_LANGUAGES = ['en', 'es', 'fr']

export interface OcrExtractedText {
  rec_text?: string
  rec_score?: number
}

export interface FuzzyResult {
  matching_name?: string
  matching_source?: string
  matching_algorithm?: string
  matching_uid?: number
  matching_row_number?: number
  distance?: number
}

export type OcrResultItem = OcrExtractedText & FuzzyResult
