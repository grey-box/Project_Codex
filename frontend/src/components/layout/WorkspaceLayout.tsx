import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Header } from './Header'
import { LeftNavBar } from './LeftNavBar'
import type { WorkspaceToolsProps } from './WorkspaceTools'
import type { LanguageOption } from '../../types/codex'

const mobileQuery = '(max-width: 767px)'
const isMobileViewport = () => window.matchMedia(mobileQuery).matches

interface WorkspaceLayoutProps extends WorkspaceToolsProps {
  languages: LanguageOption[]
  children: ReactNode
}

export function WorkspaceLayout({ languages, children, ...tools }: WorkspaceLayoutProps) {
  const { t, i18n } = useTranslation()
  const shellRef = useRef<HTMLDivElement>(null)
  const previousLanguage = useRef(i18n.language)
  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage || i18n.language
    if (previousLanguage.current === i18n.language) return
    previousLanguage.current = i18n.language
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const regions = shellRef.current?.querySelectorAll<HTMLElement>(
      '.workspace-breadcrumb, .workspace-intro, .workspace-search, .workspace-results-heading, .workspace-translation'
    )
    const animations = Array.from(regions ?? []).map(region => region.animate(
      [{ opacity: .55, transform: 'translateY(2px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 160, easing: 'cubic-bezier(.2,.8,.2,1)' }
    ))
    return () => animations.forEach(animation => animation.cancel())
  }, [i18n.language, i18n.resolvedLanguage])
  const [navigationOpen, setNavigationOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const sidebarRef = useRef<HTMLElement>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)
  const subscribe = useCallback((onChange: () => void) => {
    const query = window.matchMedia(mobileQuery)
    const handleChange = () => {
      const toolOpen = Boolean(sidebarRef.current?.querySelector('[role="dialog"]'))
      setNavigationOpen(query.matches && toolOpen)
      if (!query.matches && toolOpen) setSidebarCollapsed(false)
      onChange()
    }
    query.addEventListener('change', handleChange)
    return () => query.removeEventListener('change', handleChange)
  }, [])
  const isMobile = useSyncExternalStore(subscribe, isMobileViewport, () => false)
  const drawerOpen = isMobile && navigationOpen
  const navigationVisible = isMobile ? drawerOpen : !sidebarCollapsed
  const closeNavigation = useCallback(() => setNavigationOpen(false), [])

  useEffect(() => {
    if (!navigationVisible) return
    const toolDialog = sidebarRef.current?.querySelector<HTMLElement>('[role="dialog"]')
    // A breakpoint change can briefly hide a collapsed sidebar and blur its tool.
    if (toolDialog && !toolDialog.contains(document.activeElement)) {
      toolDialog.querySelector<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]')?.focus()
    }
  }, [navigationVisible, isMobile])

  useEffect(() => {
    if (!drawerOpen) return
    const previousOverflow = document.body.style.overflow
    const toggle = toggleRef.current
    const sidebar = sidebarRef.current
    document.body.style.overflow = 'hidden'
    const toolDialog = sidebar?.querySelector<HTMLElement>('[role="dialog"]')
    if (!toolDialog?.contains(document.activeElement)) {
      if (toolDialog) toolDialog.querySelector<HTMLElement>('button, input, select, [tabindex="0"]')?.focus()
      else sidebar?.querySelector<HTMLButtonElement>('.workspace-navigation-close')?.focus()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      // Utility dialogs and dropdowns handle their own Escape and focus first.
      if (!sidebar || sidebar.querySelector('[role="dialog"]')) return
      if (event.key === 'Escape') {
        if (sidebar.querySelector('[data-dropdown-panel]')) return
        event.preventDefault()
        closeNavigation()
      }
      if (event.key !== 'Tab') return
      const controls = Array.from(sidebar.querySelectorAll<HTMLElement>(
        'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]'
      )).filter(element => element.getClientRects().length > 0)
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      if (sidebar?.querySelector('[role="dialog"]')) return
      if (isMobileViewport()) toggle?.focus()
      else document.getElementById('drug-search')?.focus()
    }
  }, [drawerOpen, closeNavigation])

  const navigateToSearch = () => {
    closeNavigation()
    requestAnimationFrame(() => document.getElementById('drug-search')?.focus())
  }

  return (
    <div className="workspace-shell" ref={shellRef} data-sidebar-collapsed={sidebarCollapsed}>
      <a className="skip-link" href="#drug-search" inert={drawerOpen}>{t('workspace.skipToSearch')}</a>
      {drawerOpen && <button type="button" className="workspace-navigation-backdrop"
        tabIndex={-1} aria-label={t('workspace.closeNavigation')} onClick={closeNavigation} />}
      <aside id="workspace-navigation" className="workspace-sidebar" ref={sidebarRef}
        role={isMobile ? 'dialog' : undefined} aria-modal={drawerOpen || undefined}
        aria-label={t('workspace.tools')} aria-hidden={!navigationVisible || undefined}
        inert={!navigationVisible} data-open={drawerOpen}>
        <LeftNavBar {...tools} onNavigate={navigateToSearch} onCloseNavigation={closeNavigation} />
      </aside>
      <div className="workspace-content" inert={drawerOpen}>
        <Header languages={languages} navigationOpen={navigationVisible} isMobile={isMobile} toggleRef={toggleRef}
          onToggleNavigation={() => {
            if (isMobile) setNavigationOpen(open => !open)
            else setSidebarCollapsed(collapsed => !collapsed)
          }} />
        {children}
      </div>
    </div>
  )
}
