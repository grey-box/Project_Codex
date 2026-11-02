import React from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Dropdown } from '../ui'
import type { LanguageOption } from '../../types/codex'

interface LanguageSelectorProps {
  languages: LanguageOption[]
  fullWidth?: boolean
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  languages,
  fullWidth = false,
}) => {
  const { i18n } = useTranslation()

  const capitalize = (str: string) => (str ? str.charAt(0).toUpperCase() + str.slice(1) : str)
  const currentLangOption = languages.find((l) => l.code === i18n.language) || languages[0]
  const currentLangLabel = capitalize(currentLangOption?.label || i18n.language)

  const handleSelectLanguage = (code: string) => {
    i18n.changeLanguage(code)
  }

  return (
    <Dropdown
      widthClass={fullWidth ? 'w-full' : 'w-44'}
      align="right"
      className={fullWidth ? 'w-full' : ''}
      trigger={(isOpen) => (
        <Button
          type="button"
          variant="nav"
          size="md"
          fullWidth={fullWidth}
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
              />
            </svg>
          }
        >
          <span>{currentLangLabel}</span>
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </Button>
      )}
    >
      <div className="space-y-0.5">
        {languages.map((lang) => (
          <button
            key={lang.code}
            type="button"
            onClick={() => handleSelectLanguage(lang.code)}
            className={`w-full flex items-center justify-between px-3 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer text-left ${
              i18n.language === lang.code
                ? 'bg-emerald-50 text-emerald-800'
                : 'text-slate-700 hover:bg-slate-50'
            }`}
          >
            <span>{capitalize(lang.label)}</span>
            <span className="text-[10px] font-bold text-slate-400 uppercase">{lang.code}</span>
          </button>
        ))}
      </div>
    </Dropdown>
  )
}
