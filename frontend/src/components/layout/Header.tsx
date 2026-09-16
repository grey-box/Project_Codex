import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PopulateDropdown } from '../populate/PopulateDropdown'
import { ImportLanguageModal } from '../import/ImportLanguageModal'
import { LanguageSelector } from '../language/LanguageSelector'
import type { LanguageOption } from '../../types/codex'

interface HeaderProps {
  languages: LanguageOption[]
  onImportSuccess?: () => void
}

export const Header: React.FC<HeaderProps> = ({ languages, onImportSuccess }) => {
  const { t } = useTranslation()
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

  // Close on Escape key
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
      <header className="w-full h-16 bg-[#1e4840] border-b border-[#2d5850] px-4 md:px-8 sticky top-0 z-50 flex items-center shrink-0">
        <div className="max-w-7xl w-full mx-auto flex items-center justify-between">
          {/* Left side: Brand and main links */}
          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-lg md:text-xl font-bold tracking-wider text-white hover:text-emerald-200 transition-colors"
              aria-label="Grey Box home"
            >
              GREY-BOX
            </a>

            <nav className="hidden md:flex items-center gap-5 text-sm font-medium text-emerald-100">
              <a href="#" className="hover:text-white transition-colors">
                {t('nav.home') || 'Home'}
              </a>
              <a href="#" className="hover:text-white transition-colors">
                {t('nav.about') || 'About'}
              </a>
            </nav>
          </div>

          {/* Desktop Controls (md: and up) */}
          <div className="hidden md:flex items-center gap-3">
            <PopulateDropdown />
            <ImportLanguageModal onImportSuccess={onImportSuccess} />
            <LanguageSelector languages={languages} />

            <div className="hidden lg:flex items-center gap-1.5 ml-2 pl-2 border-l border-emerald-700/60">
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

              <button
                type="button"
                className="p-1.5 text-emerald-200 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                aria-label="Open LinkedIn profile"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6.4 8.7a1.7 1.7 0 110-3.4 1.7 1.7 0 010 3.4zM8 20H4.8V10H8v10zm12 0h-3.2v-5.4c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9V20H9.7V10h3.1v1.4h.1c.4-.8 1.5-1.8 3.1-1.8 3.3 0 3.9 2.2 3.9 5V20z" />
                </svg>
              </button>
            </div>
          </div>

          {/* Mobile Hamburger / Close Button (md:hidden) */}
          <div className="flex md:hidden items-center">
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              className="p-2 text-white hover:bg-emerald-800/50 rounded-lg transition-colors outline-none cursor-pointer"
              aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Fullscreen Mobile Drawer Menu below the static header */}
      {isMobileMenuOpen && (
        <div className="md:hidden fixed inset-x-0 top-16 bottom-0 z-40 bg-[#1e4840] flex flex-col justify-between p-6 overflow-y-auto animate-drawer-in">
          {/* Navigation Sections */}
          <div className="py-2 flex flex-col gap-3">
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-300/80 px-2 block mb-1">
              Navigation
            </span>
            <nav className="flex flex-col gap-2">
              <a
                href="#"
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-sm font-semibold text-white hover:text-emerald-200 py-2.5 px-3 rounded-lg hover:bg-emerald-800/40 transition-colors flex items-center gap-3"
              >
                <svg className="w-4 h-4 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>{t('nav.home') || 'Home'}</span>
              </a>
              <a
                href="#"
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-sm font-semibold text-white hover:text-emerald-200 py-2.5 px-3 rounded-lg hover:bg-emerald-800/40 transition-colors flex items-center gap-3"
              >
                <svg className="w-4 h-4 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{t('nav.about') || 'About'}</span>
              </a>
            </nav>
          </div>

          {/* Actions Section (Bottom-aligned Column) */}
          <div className="mt-auto pt-6 border-t border-emerald-800/80">
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-300/80 px-2 block mb-5">
              Database & Settings
            </span>
            <div className="flex flex-col gap-4">
              <div className="w-full">
                <PopulateDropdown fullWidth />
              </div>
              <div className="w-full">
                <ImportLanguageModal
                  fullWidth
                  onImportSuccess={() => {
                    onImportSuccess?.()
                    setIsMobileMenuOpen(false)
                  }}
                />
              </div>
              <div className="w-full pt-1 pb-4">
                <LanguageSelector languages={languages} fullWidth />
              </div>
            </div>

            {/* Social & Region Footer */}
            <div className="pt-6 border-t border-emerald-800/60 flex items-center justify-between text-emerald-300">
              <span className="text-xs font-medium text-emerald-300/70">Connect with us</span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="p-2 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                  aria-label="Open regions"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm8 10c0 1.07-.22 2.09-.61 3h-3.13a15.3 15.3 0 00.17-3 15.3 15.3 0 00-.17-3h3.13c.39.91.61 1.93.61 3zM12 20c-1.03-1.11-1.81-2.29-2.36-3.5h4.72c-.55 1.21-1.33 2.39-2.36 3.5zM9.11 15A13.3 13.3 0 018.8 12c0-1.04.11-2.04.31-3h5.78c.2.96.31 1.96.31 3 0 1.04-.11 2.04-.31 3H9.11zM4.61 15A7.97 7.97 0 014 12c0-1.07.22-2.09.61-3h3.13a15.3 15.3 0 00-.17 3c0 1.02.06 2.02.17 3H4.61zm1.01 1.5h2.43c.34.84.75 1.66 1.23 2.44a8.05 8.05 0 01-3.66-2.44zM8.05 7.5H5.62a8.05 8.05 0 013.66-2.44 14.1 14.1 0 00-1.23 2.44zm5.95-2.44a8.05 8.05 0 013.66 2.44h-2.43A14.1 14.1 0 0014 5.06zm1.95 13.88c.48-.78.89-1.6 1.23-2.44h2.43a8.05 8.05 0 01-3.66 2.44z" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="p-2 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                  aria-label="Open X profile"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.9 2h3.2l-7 8 8.2 12h-6.4L12 15l-6.2 7H2.5l7.5-8.4L2.1 2h6.5l4.4 6.3L18.9 2zm-1.1 18h1.8L7.6 4H5.7l12.1 16z" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="p-2 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                  aria-label="Open Facebook profile"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M13.5 21v-8h2.7l.4-3h-3.1V8.1c0-.9.3-1.6 1.7-1.6h1.5V3.8c-.3 0-1.2-.1-2.2-.1-2.2 0-3.8 1.3-3.8 3.8V10H8v3h2.7v8h2.8z" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="p-2 hover:text-white hover:bg-emerald-800/50 rounded-lg transition-colors cursor-pointer"
                  aria-label="Open LinkedIn profile"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6.4 8.7a1.7 1.7 0 110-3.4 1.7 1.7 0 010 3.4zM8 20H4.8V10H8v10zm12 0h-3.2v-5.4c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9V20H9.7V10h3.1v1.4h.1c.4-.8 1.5-1.8 3.1-1.8 3.3 0 3.9 2.2 3.9 5V20z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}




