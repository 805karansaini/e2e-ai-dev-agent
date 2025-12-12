function HomePage() {
  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-lg font-semibold text-slate-50">Dashboard</h2>
        <p className="mt-1 text-sm text-slate-400">
          Welcome to the end to end AI Dev Agent. Use the navigation above to create tasks,
          edit prompts, and monitor execution.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-medium text-slate-100">
            Quick start
          </h3>
          <p className="mt-2 text-sm text-slate-400">
            Start by creating a new task, then refine the agent prompt and check the
            current status as the workflow runs.
          </p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-medium text-slate-100">
            What you can do
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-400">
            <li>Create and configure new tasks</li>
            <li>Adjust prompts used by the agent</li>
            <li>Inspect current run status</li>
            <li>Review summaries and outcomes</li>
          </ul>
        </div>
      </div>
    </section>
  )
}

export default HomePage


