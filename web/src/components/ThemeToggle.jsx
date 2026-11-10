import { useEffect, useState } from 'react'

import { THEME_EVENT, currentTheme, followDevice, setTheme } from '../theme'

// The light / dark switch in the top bar (2026-10-28). It shows the theme you
// would switch TO: a sun on the dark page, a moon on the light one.
export default function ThemeToggle() {
  const [theme, setThemeState] = useState(currentTheme)

  useEffect(() => {
    const onTheme = (e) => setThemeState(e.detail)
    window.addEventListener(THEME_EVENT, onTheme)
    const stop = followDevice()
    return () => {
      window.removeEventListener(THEME_EVENT, onTheme)
      stop()
    }
  }, [])

  const next = theme === 'light' ? 'dark' : 'light'
  return (
    <button type="button" className="theme-toggle" onClick={() => setTheme(next)}
            aria-label={`Switch to the ${next} theme`} title={`Switch to the ${next} theme`}>
      {next === 'light' ? (
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" fill="none"
             stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" fill="none"
             stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
          <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  )
}
