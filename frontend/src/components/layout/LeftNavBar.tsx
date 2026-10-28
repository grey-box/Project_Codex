import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
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

    const { t } = useTranslation()
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

            {/* Bottom Footer Section */}
            <div className="p-4 border-t border-[#2d5850]/70 shrink-0 bg-[#193d36]">
                <div className="w-full mb-3">
                    <LanguageSelector languages={languages} fullWidth />
                </div>
                <p className="text-[11px] text-emerald-300/50 text-center">
                    &copy; {new Date().getFullYear()} Grey-box
                </p>
            </div>
        </aside>
    )
}