import { Outlet } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'

const THEME_STORAGE_KEY = 'ui-theme'

function getInitialTheme() {
  if (typeof window === 'undefined') return 'light'

  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored

  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches
  return prefersDark ? 'dark' : 'light'
}

function MainLayout() {
  const [theme, setTheme] = useState(getInitialTheme)

  const isDark = theme === 'dark'
  const themeLabel = isDark ? 'Light mode' : 'Dark mode'
  const themeIcon = isDark ? '☀️' : '🌙'

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    root.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [isDark, theme])

  const accentGradient = useMemo(
    () => 'from-primary via-indigo-500 to-sky-400',
    []
  )

  function toggleTheme() {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900 transition-colors duration-300 dark:from-slate-950 dark:via-slate-950 dark:to-slate-900/80 dark:text-slate-50">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 lg:py-10">
        <header className="mb-6 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/70 px-4 py-4 shadow-sm backdrop-blur-sm transition-colors duration-300 dark:border-slate-800 dark:bg-slate-900/60 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-4">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${accentGradient} text-lg font-black text-white shadow-lg shadow-primary/30`}
              aria-hidden="true"
            >
              TF
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <p className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
                  TaskForge
                </p>
                <span className="rounded-full border border-primary/30 bg-primary/10 px-2 text-xs font-semibold uppercase tracking-wide text-primary shadow-sm dark:border-primary/40 dark:bg-primary/20">
                  Live
                </span>
              </div>
              <p className="max-w-xl text-sm text-slate-500 dark:text-slate-400">
                Orchestrate tasks and subtasks with clarity and quick controls.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 shadow-sm dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300 sm:flex">
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_0_6px_rgba(52,211,153,0.15)]" />
              <span>Synced workspace</span>
            </div>
            <button
              type="button"
              onClick={toggleTheme}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm transition-colors hover:border-primary/40 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:border-primary/40 dark:hover:text-white dark:focus-visible:ring-offset-slate-900"
              aria-label={`Toggle ${themeLabel}`}
            >
              <span className="text-base" aria-hidden="true">
                {themeIcon}
              </span>
              <span>{themeLabel}</span>
            </button>
          </div>
        </header>

        <div className="glass-card flex-1 p-4 md:p-6">
          <main className="min-h-[320px]">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}

export default MainLayout


