import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Input, Modal, Select } from '../ui'
import { EXPORT_COLUMNS, getExportRecords, type ExportDataset, type ExportNameType } from '../../services/export'
import { convertJsonToCsv } from '../../utils/csvConverter'
import { downloadCsv } from '../../utils/csvDownload'
import { useToastError } from '../../services/toasts'

export function ExportModal() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [dataset, setDataset] = useState<ExportDataset>('demo')
  const [nameType, setNameType] = useState<ExportNameType>('generic')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [columns, setColumns] = useState<string[]>([...EXPORT_COLUMNS.demo])
  const [error, setError] = useState('')
  const [rangeError, setRangeError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [downloaded, setDownloaded] = useState<number | null>(null)
  const request = useRef<AbortController | null>(null)
  useToastError(error)
  useEffect(() => () => request.current?.abort(), [])
  const clearFeedback = () => { setError(''); setRangeError(false); setDownloaded(null) }
  const close = () => { request.current?.abort(); setBusy(false); clearFeedback(); setOpen(false) }

  return <>
    <Button variant="nav" onClick={() => { clearFeedback(); setOpen(true) }} icon={
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M4 15v6h16v-6" /></svg>
    }>{t('export.open')}</Button>
    <Modal isOpen={open} onClose={close} title={t('export.title')} maxWidthClass="max-w-lg">
      <form className="workspace-export" aria-busy={busy} onSubmit={async event => {
        event.preventDefault()
        if (busy || !columns.length) return
        clearFeedback()
        if (start.trim() && end.trim() && start.trim().toLowerCase() > end.trim().toLowerCase()) {
          setRangeError(true); setError(t('export.invalidRange')); document.getElementById('export-end')?.focus(); return
        }
        const controller = new AbortController()
        request.current = controller
        setBusy(true)
        try {
          const rows = await getExportRecords(dataset, nameType, start, end, controller.signal)
          if (controller.signal.aborted) return
          if (!rows.length) { setError(t('export.empty')); return }
          downloadCsv(convertJsonToCsv(rows, columns), `medications-${dataset === 'demo' ? 'initial-data' : 'rxnorm'}-${nameType}.csv`)
          setDownloaded(rows.length)
        } catch (err) {
          if (!controller.signal.aborted) setError(err instanceof Error ? err.message : t('export.failed'))
        } finally {
          if (request.current === controller) { request.current = null; setBusy(false) }
        }
      }}>
        <Select id="export-dataset" label={t('export.dataset')} value={dataset} disabled={busy}
          options={[{ value: 'demo', label: t('export.initial') }, { value: 'rxnorm', label: 'RxNorm' }]}
          onValueChange={value => { const next = value as ExportDataset; setDataset(next); setColumns([...EXPORT_COLUMNS[next]]); clearFeedback() }} />
        <fieldset className="space-y-2">
          <legend className="workspace-export-label">{t('export.nameType')}</legend>
          <div className="workspace-export-toggle" role="group" aria-label={t('export.nameType')}>
            {(['generic', 'brand'] as const).map(type => <button type="button" key={type} aria-pressed={nameType === type} disabled={busy}
              onClick={() => { setNameType(type); clearFeedback() }}>{t(`export.${type}`)}</button>)}
          </div>
        </fieldset>
        <div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input id="export-start" label={t('export.start')} value={start} disabled={busy} autoComplete="off" onChange={e => { setStart(e.target.value); clearFeedback() }} />
            <Input id="export-end" label={t('export.end')} value={end} disabled={busy} autoComplete="off" error={rangeError ? t('export.invalidRange') : undefined} onChange={e => { setEnd(e.target.value); clearFeedback() }} />
          </div>
          <p className="workspace-export-hint">{t('export.rangeHint')}</p>
        </div>
        <fieldset className="space-y-2">
          <legend className="workspace-export-label">{t('export.columns')} <span>({columns.length}/5)</span></legend>
          <div className="workspace-export-columns-heading">
            <div className="flex gap-3">
              <button type="button" disabled={busy} onClick={() => { setColumns([...EXPORT_COLUMNS[dataset]]); clearFeedback() }}>{t('tools.selectAll')}</button>
              <button type="button" disabled={busy} onClick={() => { setColumns([]); clearFeedback() }}>{t('tools.deselectAll')}</button>
            </div>
          </div>
          <div className="workspace-export-columns">
            {EXPORT_COLUMNS[dataset].map(column => <label key={column}>
              <input type="checkbox" checked={columns.includes(column)} disabled={busy} onChange={() => {
                setColumns(selected => selected.includes(column) ? selected.filter(item => item !== column) : EXPORT_COLUMNS[dataset].filter(item => selected.includes(item) || item === column)); clearFeedback()
              }} />
              <span>{column}</span>
            </label>)}
          </div>
        </fieldset>
        {downloaded !== null && <p role="status" className="workspace-export-hint">{t('export.downloaded', { count: downloaded })}</p>}
        <div className="workspace-export-actions">
          <Button type="button" variant="ghost" onClick={close}>{t('tools.cancel')}</Button>
          <Button type="submit" disabled={!columns.length} isLoading={busy}>{t(busy ? 'export.exporting' : 'export.download')}</Button>
        </div>
      </form>
    </Modal>
  </>
}
