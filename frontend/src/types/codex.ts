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

export const LANGUAGE_COUNTRY_MAP: Record<string, CountryOption[]> = {
  es: [
    { code: 'MX', label: 'Mexico' },
    { code: 'ES', label: 'Spain' },
  ],
  en: [
    { code: 'US', label: 'United States' },
    { code: 'GB', label: 'United Kingdom' },
    { code: 'CA', label: 'Canada' },
  ],
  fr: [
    { code: 'FR', label: 'France' },
    { code: 'CA', label: 'Canada' },
    { code: 'BE', label: 'Belgium' },
  ],
  ru: [
    { code: 'RU', label: 'Russia' },
  ],
  uk: [
    { code: 'UA', label: 'Ukraine' },
    { code: 'PL', label: 'Poland' },
  ],
}

export const FALLBACK_LANGUAGES = ['en', 'es', 'fr']
