import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Modal } from '../ui'

export function Documentation() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <>
      <button className="workspace-docs" type="button" onClick={() => setOpen(true)}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Zm0 0v15" /></svg>
        {t('workspace.documentation')}
      </button>
      <Modal isOpen={open} onClose={() => setOpen(false)} title={t('workspace.documentation')} maxWidthClass="max-w-2xl">
        <div className="workspace-help">
          {['search', 'translate', 'scan', 'import', 'populate'].map(section => (
            <section key={section}>
              <h4>{t(`workspace.help.${section}.title`)}</h4>
              <p>{t(`workspace.help.${section}.body`)}</p>
            </section>
          ))}
        </div>
      </Modal>
    </>
  )
}
