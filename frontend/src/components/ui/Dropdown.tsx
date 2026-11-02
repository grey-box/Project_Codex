import React, { useState, useRef, useEffect, useLayoutEffect } from 'react'

export interface DropdownProps {
  trigger: (isOpen: boolean) => React.ReactNode
  children: React.ReactNode
  align?: 'left' | 'right'
  widthClass?: string
  className?: string
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  children,
  align = 'right',
  widthClass = 'w-72 sm:w-80',
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [openUpward, setOpenUpward] = useState(false)
  const [horizontalAlign, setHorizontalAlign] = useState<'left' | 'right' | 'center'>(align)
  const [maxHeightStyle, setMaxHeightStyle] = useState<string>('calc(100vh - 120px)')

  const dropdownRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  // Smart viewport auto-positioning
  const calculatePosition = () => {
    if (!dropdownRef.current) return

    const rect = dropdownRef.current.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    const viewportWidth = window.innerWidth

    // 1. Vertical placement: Check if space below is less than 280px and space above is larger
    const spaceBelow = viewportHeight - rect.bottom
    const spaceAbove = rect.top

    const shouldOpenUp = spaceBelow < 300 && spaceAbove > spaceBelow
    setOpenUpward(shouldOpenUp)

    // Dynamic max-height based on available space
    const availableHeight = shouldOpenUp ? spaceAbove - 24 : spaceBelow - 24
    setMaxHeightStyle(`${Math.max(160, availableHeight)}px`)

    // 2. Horizontal placement: Adjust if popping outside screen
    if (viewportWidth < 640) {
      setHorizontalAlign(rect.left < 40 ? 'left' : rect.right > viewportWidth - 40 ? 'right' : 'center')
    } else {
      if (align === 'right') {
        if (rect.right < 300) {
          setHorizontalAlign('left')
        } else {
          setHorizontalAlign('right')
        }
      } else {
        if (viewportWidth - rect.left < 300) {
          setHorizontalAlign('right')
        } else {
          setHorizontalAlign('left')
        }
      }
    }
  }

  useLayoutEffect(() => {
    if (isOpen) {
      calculatePosition()
    }
  }, [isOpen])

  // Recalculate on window resize or scroll
  useEffect(() => {
    if (!isOpen) return

    const handleResizeOrScroll = () => {
      calculatePosition()
    }

    window.addEventListener('resize', handleResizeOrScroll)
    window.addEventListener('scroll', handleResizeOrScroll, true)

    return () => {
      window.removeEventListener('resize', handleResizeOrScroll)
      window.removeEventListener('scroll', handleResizeOrScroll, true)
    }
  }, [isOpen])

  // Close when clicking outside
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick)
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
    }
  }, [isOpen])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  // Compute Tailwind classes for placement
  const verticalClass = openUpward ? 'bottom-full mb-2' : 'top-full mt-2'

  const horizontalClass =
    horizontalAlign === 'center'
      ? 'left-1/2 -translate-x-1/2'
      : horizontalAlign === 'left'
      ? 'left-0'
      : 'right-0'

  const originClass = openUpward
    ? horizontalAlign === 'right'
      ? 'origin-bottom-right'
      : horizontalAlign === 'left'
      ? 'origin-bottom-left'
      : 'origin-bottom'
    : horizontalAlign === 'right'
    ? 'origin-top-right'
    : horizontalAlign === 'left'
    ? 'origin-top-left'
    : 'origin-top'

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      <div onClick={() => setIsOpen(!isOpen)}>{trigger(isOpen)}</div>

      {isOpen && (
        <div
          ref={panelRef}
          style={{ maxHeight: maxHeightStyle }}
          className={`absolute ${verticalClass} ${horizontalClass} ${widthClass} ${originClass} max-w-[calc(100vw-2rem)] overflow-y-auto overscroll-contain bg-white rounded-xl shadow-2xl border border-slate-200 z-50 p-4 animate-in fade-in zoom-in-95 duration-150`}
        >
          {children}
        </div>
      )}
    </div>
  )
}
