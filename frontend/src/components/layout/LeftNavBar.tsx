import React, { useState, useEffect } from 'react'
// import { useTranslation } from 'react-i18next'
// import { PopulateDropdown } from '../populate/PopulateDropdown'
// import { ImportLanguageModal } from '../import/ImportLanguageModal'
// import { LanguageSelector } from '../language/LanguageSelector'
// import { LanguageFilterModal } from '../language/LanguageFilterModal'
// import { OcrModal } from '../ocr/OcrModal'
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
    /*
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
     */
}) => {
    //const {t} = useTranslation()
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

    // Prevent background scrolling when mobile menu is open
    useEffect(() => {
        if (isMobileMenuOpen) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = ''
        }
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
        <>
            <aside className="hidden md:flex flex-col w-64 fixed inset-y-0 left-0">
                <div>

                </div>
            </aside>
        </>
    )
}