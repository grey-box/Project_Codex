/** Destinations are the links published in Grey-box's official website footer. */
export function SignInFooter() {
  return <footer className="workspace-signin-footer">
    <div className="workspace-signin-footer-links">
      <a href="https://www.grey-box.ca/home/" target="_blank" rel="noopener noreferrer" aria-label="Grey-box website" title="Grey-box website">
        <span>Grey-box</span>
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M14 4h6v6m0-6L10 14M10 4H4v16h16v-6" /></svg>
      </a>
      <div className="workspace-signin-socials">
        <a href="https://twitter.com/greyboxproject" target="_blank" rel="noopener noreferrer" aria-label="Grey-box on X" title="Grey-box on X">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 3h4l12 18h-4ZM20 3 4 21" /></svg>
        </a>
        <a href="https://www.facebook.com/greyboxORG/" target="_blank" rel="noopener noreferrer" aria-label="Grey-box on Facebook" title="Grey-box on Facebook">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M14 22v-9h3l.5-4H14V7c0-1 .4-2 2-2h2V1.5A20 20 0 0 0 15 1c-3 0-5 2-5 5v3H7v4h3v9Z" /></svg>
        </a>
      </div>
    </div>
    <p>© {new Date().getFullYear()} Grey-box</p>
  </footer>
}
