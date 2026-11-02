import React from 'react'

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
  const typeStyles = {
    error: 'bg-rose-50 border-rose-200 text-rose-700',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    info: 'bg-sky-50 border-sky-200 text-sky-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  }

  const icons = {
    error: '⚠️',
    success: '✅',
    info: 'ℹ️',
    warning: '⚠️',
  }

  return (
    <div
      className={`p-3 border text-xs font-medium rounded-xl flex items-center gap-2.5 ${typeStyles[type]} ${className}`}
      role="alert"
    >
      <span className="shrink-0">{icons[type]}</span>
      <div className="flex-1">{message || children}</div>
    </div>
  )
}
