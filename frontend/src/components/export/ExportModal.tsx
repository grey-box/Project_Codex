import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Input, Modal, Select } from '../ui'
import {
  getExportRecords,
  type ExportReportType,
  type ExportNameType,
} from '../../services/export'
import {
  convertJsonToCsv,
  type CsvRecord,
} from '../../utils/csvConverter'
import { downloadCsv } from '../../utils/csvDownload'
import { useToastError } from '../../services/toasts'

export function ExportModal() {
  const { t } = useTranslation()

  const [open, setOpen] = useState(false)
  const [reportType, setReportType] =
    useState<ExportReportType>('medication')
  const [nameType, setNameType] =
    useState<ExportNameType>('generic')

  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  const [rows, setRows] = useState<CsvRecord[]>([])
  const [availableColumns, setAvailableColumns] =
    useState<string[]>([])
  const [columns, setColumns] = useState<string[]>([])

  const [error, setError] = useState('')
  const [rangeError, setRangeError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [downloaded, setDownloaded] = useState<number | null>(null)

  const request = useRef<AbortController | null>(null)

  useToastError(error)

  useEffect(() => () => request.current?.abort(), [])

  const clearFeedback = () => {
    setError('')
    setRangeError(false)
    setDownloaded(null)
  }

  // Clear previous results whenever the filters change.
  const resetResults = () => {
    request.current?.abort()
    request.current = null
    setBusy(false)
    setRows([])
    setAvailableColumns([])
    setColumns([])
    clearFeedback()
  }

  const close = () => {
    resetResults()
    setOpen(false)
  }

  const searchRecords = async () => {
    if (busy) return

    clearFeedback()

    if (
      start.trim() &&
      end.trim() &&
      start.trim().toLowerCase() > end.trim().toLowerCase()
    ) {
      setRangeError(true)
      setError(t('export.invalidRange'))
      document.getElementById('export-end')?.focus()
      return
    }

    const controller = new AbortController()
    request.current = controller

    setBusy(true)
    setRows([])
    setAvailableColumns([])
    setColumns([])

    try {
      const results = await getExportRecords(
        reportType,
        nameType,
        start,
        end,
        controller.signal,
      )

      if (controller.signal.aborted) return

      if (!results.length) {
        setError(t('export.empty'))
        return
      }

      // Find every property across all returned JSON records.
      const discoveredColumns = Array.from(
        new Set(
          results.flatMap(record => Object.keys(record)),
        ),
      )

      setRows(results)
      setAvailableColumns(discoveredColumns)
      setColumns([...discoveredColumns])
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(
          err instanceof Error ? err.message : t('export.failed'),
        )
      }
    } finally {
      if (request.current === controller) {
        request.current = null
        setBusy(false)
      }
    }
  }

  const exportCsv = () => {
    if (!rows.length || !columns.length || busy) return

    clearFeedback()

    try {
      const csv = convertJsonToCsv(rows, columns)

      const filename = reportType === 'medication'
        ? `medications-rxnorm-${nameType}.csv`
        : 'clinical-icd11.csv'

      downloadCsv(csv, filename)
      setDownloaded(rows.length)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t('export.failed'),
      )
    }
  }

  return (
    <>
      <Button
        variant="nav"
        fullWidth
        onClick={() => {
          clearFeedback()
          setOpen(true)
        }}
        icon={
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path d="M12 3v12m-4-4 4 4 4-4M4 15v6h16v-6" />
          </svg>
        }
      >
        {t('export.open')}
      </Button>

      <Modal
        isOpen={open}
        onClose={close}
        title={t('export.title')}
        maxWidthClass="max-w-lg"
      >
        <form
          className="workspace-export"
          aria-busy={busy}
          onSubmit={event => {
            event.preventDefault()
            void searchRecords()
          }}
        >
          <Select
            id="export-report-type"
            label="Report type"
            value={reportType}
            disabled={busy}
            options={[
              { value: 'medication', label: 'Medication' },
              { value: 'clinical', label: 'Clinical Findings' },
            ]}
            onValueChange={value => {
              setReportType(value as ExportReportType)
              resetResults()
            }}
          />

          {reportType === 'medication' && (
            <fieldset className="space-y-2">
              <legend className="workspace-export-label">
                {t('export.nameType')}
              </legend>

              <div
                className="workspace-export-toggle"
                role="group"
                aria-label={t('export.nameType')}
              >
                {(['generic', 'brand'] as const).map(type => (
                  <button
                    type="button"
                    key={type}
                    aria-pressed={nameType === type}
                    disabled={busy}
                    onClick={() => {
                      setNameType(type)
                      resetResults()
                    }}
                  >
                    {t(`export.${type}`)}
                  </button>
                ))}
              </div>
            </fieldset>
          )}

          <div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                id="export-start"
                label={t('export.start')}
                value={start}
                disabled={busy}
                autoComplete="off"
                onChange={event => {
                  setStart(event.target.value)
                  resetResults()
                }}
              />

              <Input
                id="export-end"
                label={t('export.end')}
                value={end}
                disabled={busy}
                autoComplete="off"
                error={
                  rangeError
                    ? t('export.invalidRange')
                    : undefined
                }
                onChange={event => {
                  setEnd(event.target.value)
                  resetResults()
                }}
              />
            </div>

            <p className="workspace-export-hint">
              {t('export.rangeHint')}
            </p>
          </div>

          <div className="workspace-export-actions">
            <Button
              type="submit"
              isLoading={busy}
            >
              {busy ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {rows.length > 0 && (
            <>
              <p
                role="status"
                className="workspace-export-hint"
              >
                Found {rows.length.toLocaleString()} records.
                Choose which columns to include.
              </p>

              <fieldset className="space-y-2">
                <legend className="workspace-export-label">
                  {t('export.columns')}{' '}
                  <span>
                    ({columns.length}/{availableColumns.length})
                  </span>
                </legend>

                <div className="workspace-export-columns-heading">
                  <div className="flex gap-3">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        setColumns([...availableColumns])
                        clearFeedback()
                      }}
                    >
                      {t('tools.selectAll')}
                    </button>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        setColumns([])
                        clearFeedback()
                      }}
                    >
                      {t('tools.deselectAll')}
                    </button>
                  </div>
                </div>

                <div className="workspace-export-columns">
                  {availableColumns.map(column => (
                    <label key={column}>
                      <input
                        type="checkbox"
                        checked={columns.includes(column)}
                        disabled={busy}
                        onChange={() => {
                          setColumns(selected =>
                            selected.includes(column)
                              ? selected.filter(
                                  item => item !== column,
                                )
                              : availableColumns.filter(
                                  item =>
                                    selected.includes(item) ||
                                    item === column,
                                ),
                          )
                          clearFeedback()
                        }}
                      />
                      <span>{column}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </>
          )}

          {downloaded !== null && (
            <p
              role="status"
              className="workspace-export-hint"
            >
              {t('export.downloaded', {
                count: downloaded,
              })}
            </p>
          )}

          <div className="workspace-export-actions">
            <Button
              type="button"
              variant="ghost"
              onClick={close}
            >
              {t('tools.cancel')}
            </Button>

            <Button
              type="button"
              disabled={
                busy ||
                !rows.length ||
                !columns.length
              }
              onClick={exportCsv}
            >
              {t('export.download')}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
