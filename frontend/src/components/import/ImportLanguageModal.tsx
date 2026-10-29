import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Modal, Button, Alert } from '../ui'

const API_BASE_URL = 'http://localhost:8000'

interface ImportLanguageModalProps {
  onImportSuccess?: () => void
  fullWidth?: boolean
}

export const ImportLanguageModal: React.FC<ImportLanguageModalProps> = ({
  onImportSuccess,
  fullWidth = false,
}) => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [importMessage, setImportMessage] = useState('')
  const [importError, setImportError] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateAndSetFile = async (file: File) => {
    setImportError('')
    setImportMessage('')

    if (!file.name.toLowerCase().endsWith('.json')) {
      setImportError('El archivo debe tener extensión .json.')
      setSelectedFile(null)
      return
    }

    try {
      const text = await file.text()
      const json = JSON.parse(text)

      if (!json || typeof json !== 'object' || Array.isArray(json)) {
        throw new Error('El JSON debe ser un objeto válido.')
      }

      if (!json.language || !json.language.code || !Array.isArray(json.terms)) {
        throw new Error("El archivo no tiene el formato de Language Pack (debe incluir 'language.code' y la lista 'terms').")
      }

      setSelectedFile(file)
      setImportError('')
    } catch (err) {
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setImportError(err instanceof SyntaxError ? 'El archivo está corrupto o no es un JSON válido.' : (err as Error).message)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    setImportMessage('')
    setImportError('')

    if (!selectedFile) {
      setImportError('Por favor selecciona un archivo .json válido primero.')
      return
    }

    setIsImporting(true)
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch(`${API_BASE_URL}/packs/load`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => null)
        throw new Error(errData?.detail || 'Failed to import language pack')
      }

      const data = await response.json()
      setImportMessage(data.message || 'Language pack imported successfully!')
      onImportSuccess?.()
      setTimeout(() => {
        resetAndClose()
      }, 1500)
    } catch (error) {
      setImportError((error as Error).message)
    } finally {
      setIsImporting(false)
    }
  }

  const resetAndClose = () => {
    setIsOpen(false)
    setSelectedFile(null)
    setImportError('')
    setImportMessage('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <>
      {/* Trigger Button */}
      <Button
        variant="nav"
        size="md"
        fullWidth={fullWidth}
        onClick={() => setIsOpen(true)}
        icon={
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        }
      >
        <span>{t('home.importTitle') || 'Import Language'}</span>
      </Button>

      {/* Modal Dialog */}
      <Modal
        isOpen={isOpen}
        onClose={resetAndClose}
        title={t('home.importTitle') || 'Import Language Pack'}
        subtitle="Upload a standardized .json language pack to Neo4j"
        icon="📁"
      >
        <form onSubmit={handleUpload} className="space-y-4">
          {/* Drag & Drop Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-emerald-500 bg-emerald-50/50'
                : selectedFile
                ? 'border-emerald-300 bg-emerald-50/20'
                : 'border-slate-300 hover:border-emerald-400 hover:bg-slate-50/60'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
            />

            {selectedFile ? (
              <div className="flex flex-col items-center gap-1.5">
                <span className="text-2xl">📄</span>
                <span className="text-sm font-semibold text-slate-800">{selectedFile.name}</span>
                <span className="text-xs text-slate-400">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>
                <span className="text-xs text-emerald-600 font-medium underline mt-1">
                  Click to choose another file
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 bg-slate-100 rounded-full text-slate-500">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <div>
                  <span className="text-sm font-semibold text-emerald-700">Click to upload</span>
                  <span className="text-sm text-slate-600"> or drag and drop</span>
                </div>
                <p className="text-xs text-slate-400">Supported format: JSON (.json)</p>
              </div>
            )}
          </div>

          {/* Status Messages */}
          {importError && <Alert type="error" message={importError} />}
          {importMessage && <Alert type="success" message={importMessage} />}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={resetAndClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isImporting}
              disabled={!selectedFile}
            >
              Upload Pack
            </Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
