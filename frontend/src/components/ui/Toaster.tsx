import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { ToastContext } from '../../services/toasts'

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [toasts, setToasts] = useState<{ id: string; message: string }[]>([])
  const dismiss = useCallback((id: string) => setToasts(items => items.filter(item => item.id !== id)), [])
  const publish = useCallback((id: string, message: string) => {
    setToasts(items => [...items.filter(item => item.id !== id), { id, message }].slice(-3))
  }, [])
  const context = useMemo(() => ({ publish, dismiss }), [publish, dismiss])
  return <ToastContext.Provider value={context}>
    {children}
    {createPortal(<div className="workspace-toasts">
      {toasts.map(toast => <div className="workspace-toast" role="alert" key={toast.id}>
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v6m0 3h.01" /></svg>
        <p>{toast.message}</p>
        <button type="button" aria-label={t('tools.dismissMessage')} onClick={() => dismiss(toast.id)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" /></svg>
        </button>
      </div>)}
    </div>, document.body)}
  </ToastContext.Provider>
}
