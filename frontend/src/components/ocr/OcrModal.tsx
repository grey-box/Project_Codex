import React, { useState, useRef } from 'react'
import { Modal, Button, Alert } from '../ui'
import { scanOcrImage } from '../../services/api'
import type { OcrResultItem } from '../../types/codex'

export interface OcrModalProps {
  onSelectTerm: (term: string) => void
  currentLanguage?: string
  fullWidth?: boolean
  triggerClassName?: string
}

export const OcrModal: React.FC<OcrModalProps> = ({
  onSelectTerm,
  currentLanguage,
  fullWidth = false,
  triggerClassName,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [ocrError, setOcrError] = useState('')
  const [ocrResults, setOcrResults] = useState<OcrResultItem[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File) => {
    setOcrError('')
    setOcrResults([])

    if (!file.type.startsWith('image/')) {
      setOcrError('Please upload a valid image file (PNG, JPG, JPEG, WEBP).')
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    setSelectedFile(file)
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0])
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
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    setOcrError('')
    setOcrResults([])

    if (!selectedFile) {
      setOcrError('Please select or drop an image file first.')
      return
    }

    setIsScanning(true)
    try {
      const results = await scanOcrImage(selectedFile, currentLanguage)
      setOcrResults(results)
      if (results.length === 0) {
        setOcrError('No drug names or text recognized in this image.')
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : 'Failed to scan image')
    } finally {
      setIsScanning(false)
    }
  }

  const handleUseTerm = (term: string) => {
    onSelectTerm(term)
    resetAndClose()
  }

  const resetAndClose = () => {
    setIsOpen(false)
    setSelectedFile(null)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
    setOcrError('')
    setOcrResults([])
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
        className={triggerClassName}
        icon={
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        }
      >
        <span>OCR Scan</span>
      </Button>

      {/* Modal Dialog */}
      <Modal
        isOpen={isOpen}
        onClose={resetAndClose}
        title="Scan Image for Drug Names (OCR)"
        subtitle="Extract medication text and find fuzzy matches in the knowledge graph"
        maxWidthClass="max-w-2xl"
        icon={
          <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        }
      >
        <div className="space-y-5">
          <form onSubmit={handleScan} className="space-y-4">
            {/* Upload & Drag Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-colors ${
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
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />

              {previewUrl ? (
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <img
                    src={previewUrl}
                    alt="Uploaded preview"
                    className="w-24 h-24 object-cover rounded-lg border border-slate-200 shadow-xs"
                  />
                  <div className="text-left">
                    <p className="text-sm font-semibold text-slate-800 break-all">{selectedFile?.name}</p>
                    <p className="text-xs text-slate-400">
                      {selectedFile ? (selectedFile.size / 1024).toFixed(1) : 0} KB
                    </p>
                    <p className="text-xs text-emerald-600 font-medium underline mt-1">
                      Click to choose another image
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <div className="p-3 bg-slate-100 rounded-full text-slate-500">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-emerald-700">Click to upload image</span>
                    <span className="text-sm text-slate-600"> or drag and drop</span>
                  </div>
                  <p className="text-xs text-slate-400">Supported formats: PNG, JPG, JPEG, WEBP</p>
                </div>
              )}
            </div>

            {/* Error message */}
            {ocrError && <Alert type="error" message={ocrError} />}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-1">
              <Button type="button" variant="ghost" size="sm" onClick={resetAndClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isScanning}
                disabled={!selectedFile}
              >
                {isScanning ? 'Extracting Text...' : 'Extract & Match'}
              </Button>
            </div>
          </form>

          {/* Results Table */}
          {ocrResults.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-slate-800">
                  Extracted Terms & Matches ({ocrResults.length})
                </h4>
                <span className="text-xs text-slate-500">Select a term to search directly</span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                      <th className="py-2.5 px-3">Term / Text</th>
                      <th className="py-2.5 px-3">Confidence / Distance</th>
                      <th className="py-2.5 px-3">Source</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ocrResults.map((item, idx) => {
                      const termName =
                        item.matching_name ||
                        item.rec_text ||
                        'Unknown'
                      const detail =
                        item.rec_score !== undefined
                          ? `${(item.rec_score * 100).toFixed(1)}%`
                          : item.distance !== undefined
                          ? `Dist: ${item.distance}`
                          : '-'
                      const source = item.matching_source || 'PaddleOCR'

                      return (
                        <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-2 px-3 font-semibold text-slate-800">{termName}</td>
                          <td className="py-2 px-3 text-slate-600">
                            <span className="inline-block px-2 py-0.5 rounded-full bg-slate-100 font-medium">
                              {detail}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-500 text-[11px]">{source}</td>
                          <td className="py-2 px-3 text-right">
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              onClick={() => handleUseTerm(termName)}
                              className="font-medium text-xs px-2 py-1"
                            >
                              Use in Search
                            </Button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </>
  )
}
