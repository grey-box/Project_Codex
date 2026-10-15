import React from 'react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'nav' | 'secondary' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  icon?: React.ReactNode
  fullWidth?: boolean
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  fullWidth = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:cursor-not-allowed cursor-pointer'

  const variantStyles = {
    primary:
      'bg-[#4e7f77] hover:bg-[#3d6861] active:scale-[0.98] text-white shadow-sm disabled:bg-slate-300 disabled:text-slate-500',
    nav:
      'bg-[#3d6861] hover:bg-[#325650] active:scale-[0.98] text-white shadow-sm border border-[#5d8d85] disabled:opacity-60',
    secondary:
      'bg-slate-100 hover:bg-slate-200 text-slate-800 disabled:bg-slate-50 disabled:text-slate-400',
    outline:
      'border border-slate-300 hover:bg-slate-50 text-slate-700 disabled:opacity-50',
    ghost:
      'hover:bg-slate-100 text-slate-600 hover:text-slate-900 disabled:opacity-50',
  }

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 rounded-md gap-1.5',
    md: 'text-sm px-3.5 py-1.5 rounded-lg gap-2',
    lg: 'text-base px-5 py-2.5 rounded-xl gap-2.5',
  }

  return (
    <button
      className={`${baseStyles} ${fullWidth ? 'w-full' : ''} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {icon && <span className="shrink-0">{icon}</span>}
          {children}
        </>
      )}
    </button>
  )
}
