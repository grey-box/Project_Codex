import { createContext, useContext, useEffect, useId } from 'react'

export const ToastContext = createContext<{
  publish: (id: string, message: string) => void
  dismiss: (id: string) => void
} | null>(null)

/** One toast per error source; clearing or unmounting that error removes it. */
export function useToastError(message: string | undefined) {
  const context = useContext(ToastContext)
  const id = useId()
  const publish = context?.publish
  const dismiss = context?.dismiss
  useEffect(() => {
    if (!message || !publish || !dismiss) return
    publish(id, message)
    return () => dismiss(id)
  }, [message, id, publish, dismiss])
}
