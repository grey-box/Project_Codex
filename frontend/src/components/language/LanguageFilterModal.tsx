import React, { useState } from 'react'
import { Modal, Button } from '../ui'
import type { LanguageOption } from '../../types/codex'

export interface LanguageFilterModalProps {
  allLanguages: LanguageOption[]
  selectedLanguages: string[]
  onToggleLanguage: (code: string) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  onApply: () => void
  fullWidth?: boolean
}

export const LanguageFilterModal: React.FC<LanguageFilterModalProps> = ({
  allLanguages,
  selectedLanguages,
  onToggleLanguage,
  onSelectAll,
  onDeselectAll,
  onApply,
  fullWidth = false,
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const handleApply = () => {
    onApply()
    setIsOpen(false)
  }

  return (
    <>
      <Button
        variant="nav"
        size="md"
        fullWidth={fullWidth}
        onClick={() => setIsOpen(true)}
        icon={
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
        }
      >
        <span>
          Filter Languages ({selectedLanguages.length}/{allLanguages.length})
        </span>
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Filter Active Languages"
        subtitle="Select which languages to enable across search and translation features"
        maxWidthClass="max-w-md"
        icon={
          <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
        }
      >
        <div className="space-y-4">
          {/* Quick select actions */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs border-b border-slate-100 pb-2">
            <span className="text-slate-500 font-medium">Quick Selection:</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onSelectAll}
                className="text-emerald-700 hover:text-emerald-800 font-semibold cursor-pointer underline"
              >
                Select All
              </button>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={onDeselectAll}
                className="text-slate-600 hover:text-slate-800 font-semibold cursor-pointer underline"
              >
                Deselect All
              </button>
            </div>
          </div>

          {/* Language Checkbox List */}
          <div className="max-h-64 overflow-y-auto space-y-1.5 pr-1">
            {allLanguages.map((lang) => {
              const isChecked = selectedLanguages.includes(lang.code)
              return (
                <label
                  key={`filter-${lang.code}`}
                  className={`flex items-center justify-between p-2 rounded-lg border text-sm cursor-pointer transition-colors ${
                    isChecked
                      ? 'border-emerald-200 bg-emerald-50/50 text-emerald-900 font-medium'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggleLanguage(lang.code)}
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                    />
                    <span>{lang.label}</span>
                  </div>
                  <span className="text-xs uppercase font-mono text-slate-400 font-bold px-1.5 py-0.5 bg-slate-100 rounded">
                    {lang.code}
                  </span>
                </label>
              )
            })}
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={selectedLanguages.length === 0}
              onClick={handleApply}
            >
              Apply Filter ({selectedLanguages.length})
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
