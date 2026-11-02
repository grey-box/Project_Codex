/** Destinations are the links published in Grey-box's official website footer. */
export function WorkspaceFooter() {
  return <footer className="workspace-footer">
    <div>
      <a href="https://www.grey-box.ca/home/" target="_blank" rel="noopener noreferrer" aria-label="Grey-box website" title="Grey-box website">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><ellipse cx="12" cy="12" rx="4" ry="9" /><path d="M3 12h18M5 7h14M5 17h14" /></svg>
      </a>
      <a href="https://twitter.com/greyboxproject" target="_blank" rel="noopener noreferrer" aria-label="Grey-box on X" title="Grey-box on X">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 3h4l12 18h-4ZM20 3 4 21" /></svg>
      </a>
      <a href="https://www.facebook.com/greyboxORG/" target="_blank" rel="noopener noreferrer" aria-label="Grey-box on Facebook" title="Grey-box on Facebook">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M14 22v-9h3l.5-4H14V7c0-1 .4-2 2-2h2V1.5A20 20 0 0 0 15 1c-3 0-5 2-5 5v3H7v4h3v9Z" /></svg>
      </a>
    </div>
    <p>© {new Date().getFullYear()} Grey-box</p>
  </footer>
}
