import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Home', exact: true },
  { to: '/create-task', label: 'Create Task' },
  { to: '/prompt-editor', label: 'Prompt Editor' },
  { to: '/status', label: 'Status' },
  { to: '/summary', label: 'Summary' },
]

function getNavLinkClass(isActive) {
  const base =
    'inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium transition-colors'

  if (isActive) {
    return `${base} bg-primary text-slate-50 shadow`
  }

  return `${base} bg-slate-800/60 text-slate-300 hover:bg-slate-700/80`
}

function MainLayout() {
  return (
    <div className="min-h-screen bg-background-softer text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 lg:py-10">
        <header className="mb-6 flex flex-col gap-3 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-50 sm:text-2xl">
              AI Dev Agent
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Create, track and review AI-driven development tasks.
            </p>
          </div>
        </header>

        <div className="glass-card flex-1 p-4 shadow-soft md:p-6">
          <nav className="mb-5 flex flex-wrap gap-2 border-b border-slate-800 pb-3">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                className={({ isActive }) => getNavLinkClass(isActive)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <main className="min-h-[320px]">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}

export default MainLayout


