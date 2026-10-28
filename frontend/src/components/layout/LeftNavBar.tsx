import React, { useState, useEffect } from 'react'
// import { useTranslation } from 'react-i18next'
import { PopulateDropdown } from '../populate/PopulateDropdown'
import { ImportLanguageModal } from '../import/ImportLanguageModal'
import { LanguageSelector } from '../language/LanguageSelector'
import { LanguageFilterModal } from '../language/LanguageFilterModal'
import { OcrModal } from '../ocr/OcrModal'
import type { LanguageOption } from '../../types/codex'

interface LeftNavBarProps {
    languages: LanguageOption[]
    onImportSuccess?: () => void
    onSelectTerm?: (term: string) => void
    currentSearchLanguage?: string
    allLoadedLanguages?: LanguageOption[]
    selectedLanguages?: string[]
    onToggleLanguage?: (code: string) => void
    onSelectAllLanguages?: () => void
    onDeselectAllLanguages?: () => void
    onApplyLanguageFilter?: () => void
}

export const LeftNavBar: React.FC<LeftNavBarProps> = ({
    languages,
    onImportSuccess,
    onSelectTerm,
    currentSearchLanguage,
    allLoadedLanguages,
    selectedLanguages,
    onToggleLanguage,
    onSelectAllLanguages,
    onDeselectAllLanguages,
    onApplyLanguageFilter,
    }) => {

    //const { t } = useTranslation()
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

    // Prevent background scrolling when mobile menu is open
    useEffect(() => {
        document.body.style.overflow = isMobileMenuOpen ? 'hidden' : ''
        return () => {
            document.body.style.overflow = ''
        }
    }, [isMobileMenuOpen])

    // Close mobile menu on Escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isMobileMenuOpen) {
                setIsMobileMenuOpen(false)
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isMobileMenuOpen])

    return (
        <aside className="hidden md:flex flex-col h-screen w-64 fixed inset-y-0 left-0 bg-[#1e4840] border-r border-[#2d5850] z-40 select-none">
            {/* Brand / Logo Header */}
            <div className="p-6 border-b border-[#2d5850]/70 flex flex-col items-center text-center shrink-0">
                <a
                    href="#"
                    className="text-2xl font-extrabold tracking-wider text-white hover:text-emerald-200 transition-colors"
                    aria-label="Codex home"
                >
                    CODEX
                </a>
                <span className="text-xs font-medium text-emerald-200/70 tracking-widest uppercase mt-1">
                    by Grey-box
                </span>
            </div>

            {/* Main Navigation Controls */}
            <nav className="flex-1 px-4 py-6 space-y-6 scrollbar-thin scrollbar-thumb-emerald-800">
                {/*TODO: Access control DB and Import section */}
                {/* Database & Import Group */}
                <div>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-300/60 px-2 block mb-2">
                        Database & Import
                    </span>
                    <div className="space-y-2">
                        <div className="w-full">
                            <PopulateDropdown fullWidth />
                        </div>
                        <div className="w-full">
                            <ImportLanguageModal
                                fullWidth
                                onImportSuccess={onImportSuccess}
                            />
                        </div>
                    </div>
                </div>

                {/* OCR & Search Tools */}
                {onSelectTerm && (
                    <div>
                        <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-300/60 px-2 block mb-2">
                            Tools
                        </span>
                        <div className="w-full">
                            <OcrModal
                                fullWidth
                                onSelectTerm={onSelectTerm}
                                currentLanguage={currentSearchLanguage}
                            />
                        </div>
                    </div>
                )}

                {/* Language Filters */}
                {
                    allLoadedLanguages &&
                    selectedLanguages &&
                    onToggleLanguage &&
                    onSelectAllLanguages &&
                    onDeselectAllLanguages &&
                    onApplyLanguageFilter && (
                        <div>
                            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-300/60 px-2 block mb-2">
                                Filters
                            </span>
                            <div className="w-full">
                                <LanguageFilterModal
                                    fullWidth
                                    allLanguages={allLoadedLanguages}
                                    selectedLanguages={selectedLanguages}
                                    onToggleLanguage={onToggleLanguage}
                                    onSelectAll={onSelectAllLanguages}
                                    onDeselectAll={onDeselectAllLanguages}
                                    onApply={onApplyLanguageFilter}
                                />
                            </div>
                        </div>
                    )}
            </nav>

            {/* Login */}
            <div></div>

            {/* Bottom Footer Section */}
            <div className="p-4 border-t center-items border-[#2d5850]/70 shrink-0 bg-[#193d36]">
                <div className="w-full mb-2">
                    <LanguageSelector languages={languages} fullWidth />
                </div>
                <div className="hidden pb-2 lg:flex gap-5 items-center justify-center">
                    <button
                        type="button"
                        className="p-1.5 text-emerald-200 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                        aria-label="Open regions"
                    >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm8 10c0 1.07-.22 2.09-.61 3h-3.13a15.3 15.3 0 00.17-3 15.3 15.3 0 00-.17-3h3.13c.39.91.61 1.93.61 3zM12 20c-1.03-1.11-1.81-2.29-2.36-3.5h4.72c-.55 1.21-1.33 2.39-2.36 3.5zM9.11 15A13.3 13.3 0 018.8 12c0-1.04.11-2.04.31-3h5.78c.2.96.31 1.96.31 3 0 1.04-.11 2.04-.31 3H9.11zM4.61 15A7.97 7.97 0 014 12c0-1.07.22-2.09.61-3h3.13a15.3 15.3 0 00-.17 3c0 1.02.06 2.02.17 3H4.61zm1.01 1.5h2.43c.34.84.75 1.66 1.23 2.44a8.05 8.05 0 01-3.66-2.44zM8.05 7.5H5.62a8.05 8.05 0 013.66-2.44 14.1 14.1 0 00-1.23 2.44zm5.95-2.44a8.05 8.05 0 013.66 2.44h-2.43A14.1 14.1 0 0014 5.06zm1.95 13.88c.48-.78.89-1.6 1.23-2.44h2.43a8.05 8.05 0 01-3.66 2.44z" />
                        </svg>
                    </button>

                    <button
                        type="button"
                        className="p-1.5 text-emerald-200 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                        aria-label="Open X profile"
                    >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M18.9 2h3.2l-7 8 8.2 12h-6.4L12 15l-6.2 7H2.5l7.5-8.4L2.1 2h6.5l4.4 6.3L18.9 2zm-1.1 18h1.8L7.6 4H5.7l12.1 16z" />
                        </svg>
                    </button>

                    <button
                        type="button"
                        className="p-1.5 text-emerald-200 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                        aria-label="Open Facebook profile"
                    >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M13.5 21v-8h2.7l.4-3h-3.1V8.1c0-.9.3-1.6 1.7-1.6h1.5V3.8c-.3 0-1.2-.1-2.2-.1-2.2 0-3.8 1.3-3.8 3.8V10H8v3h2.7v8h2.8z" />
                        </svg>
                    </button>
                </div>
                <p className="text-[11px] text-emerald-300/50 text-center">
                    &copy; {new Date().getFullYear()} Grey-box
                </p>
            </div>
        </aside>
    )
}
