import { Outlet } from 'react-router-dom'

function MainLayout() {
  return (
    <div className="min-h-screen bg-background-softer text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 lg:py-10">
        <header className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
              Task Management
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Manage and execute development tasks in a single unified view.
            </p>
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


