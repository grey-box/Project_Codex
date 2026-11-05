import React from 'react'
import { useToastError } from '../../services/toasts'

export interface AlertProps {
  type?: 'error' | 'success' | 'info' | 'warning'
  message?: string
  children?: React.ReactNode
  className?: string
}

export const Alert: React.FC<AlertProps> = ({
  type = 'error',
  message,
  children,
  className = '',
}) => {
  useToastError(type === 'error' ? message : undefined)
  if (type === 'error') return null
  const typeStyles = {
    error: 'bg-rose-50 border-rose-200 text-rose-700',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    info: 'bg-sky-50 border-sky-200 text-sky-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  }

  return (
    <div
      className={`workspace-alert p-3 border text-xs font-medium rounded-xl flex items-center gap-2.5 ${typeStyles[type]} ${className}`}
      data-tone={type}
      role={type === 'warning' ? 'alert' : 'status'}
    >
      <svg className="shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d={type === 'success' ? 'm8 12 3 3 5-6' : 'M12 7v6m0 3h.01'} />
      </svg>
      <div className="flex-1">{message || children}</div>
    </div>
  )
}
