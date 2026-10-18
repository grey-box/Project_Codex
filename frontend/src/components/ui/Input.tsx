import React from 'react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  icon?: React.ReactNode
  error?: string
}

export const Input: React.FC<InputProps> = ({
  label,
  icon,
  error,
  className = '',
  id,
  disabled,
  ...props
}) => {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label
          htmlFor={id}
          className="text-xs font-semibold text-slate-700 tracking-wide uppercase"
        >
          {label}
        </label>
      )}
      <div className="relative w-full">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            {icon}
          </div>
        )}
        <input
          id={id}
          disabled={disabled}
          className={`w-full py-2.5 bg-white border rounded-xl text-sm text-slate-900 placeholder:text-slate-400 shadow-xs transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed ${
            icon ? 'pl-10 pr-4' : 'px-3.5'
          } ${
            error
              ? 'border-rose-300 focus:ring-rose-400 focus:border-rose-400'
              : 'border-slate-300 hover:border-slate-400'
          } ${className}`}
          {...props}
        />
      </div>
      {error && <span className="text-xs text-rose-600 font-medium">{error}</span>}
    </div>
  )
}
