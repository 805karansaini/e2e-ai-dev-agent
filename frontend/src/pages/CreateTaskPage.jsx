import { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.BACKEND_URL || 'http://127.0.0.1:8080'

function CreateTaskPage() {
  const [taskId, setTaskId] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [baseBranch, setBaseBranch] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()

    const trimmedTaskId = taskId.trim()
    const trimmedRepoUrl = repoUrl.trim()
    const trimmedBaseBranch = baseBranch.trim()

    if (!trimmedTaskId || !trimmedRepoUrl) {
      toast.error('Please provide both Task ID and Repository URL.')
      return
    }

    setIsSubmitting(true)
    setResult(null)

    try {
      const response = await axios.post(`${API_BASE_URL}/tasks/orchestrator`, {
        task_id: trimmedTaskId,
        repo_url: trimmedRepoUrl,
        // Let the backend apply its default if base_branch is empty
        ...(trimmedBaseBranch ? { base_branch: trimmedBaseBranch } : {}),
      })

      const data = response?.data?.data ?? null
      setResult(data)
      toast.success('Task plan generated.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error creating task plan:', error)

      let message = 'Failed to create task plan.'

      if (error.response) {
        message =
          error.response.data?.message ||
          error.response.data?.detail ||
          message
      } else if (error.request) {
        message =
          'No response from API. Please verify the backend is running and reachable.'
      } else if (error.message) {
        message = error.message
      }

      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-50">Create Task</h2>
        <p className="mt-1 text-sm text-slate-400">
          Provide the core task information used by the orchestrator:
          <span className="font-semibold text-slate-200"> task_id</span>,{' '}
          <span className="font-semibold text-slate-200">repo_url</span>, and{' '}
          <span className="font-semibold text-slate-200">base_branch</span>.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-100">Task ID</span>
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="e.g. TASK-1234"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
            <span className="text-xs text-slate-500">
              This should match the identifier you will use throughout the system.
            </span>
          </label>

          <label className="flex flex-col gap-1 text-sm md:col-span-1">
            <span className="font-medium text-slate-100">Repository URL or Path</span>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="e.g. https://github.com/user/repo.git"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </label>
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-100">Base Branch</span>
          <input
            type="text"
            value={baseBranch}
            onChange={(e) => setBaseBranch(e.target.value)}
            placeholder="Leave empty to use the API default (e.g. main)"
            className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <span className="text-xs text-slate-500">
            Optional – if omitted, the backend will use its configured default base
            branch.
          </span>
        </label>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Creating…' : 'Create Task Plan'}
          </button>
        </div>
      </form>

      {result && (
        <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="space-y-0.5">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Task Metadata
              </p>
              <p className="text-sm font-medium text-slate-100">
                {result.task_id}{' '}
                <span className="text-slate-500">
                  ({result.repo_url} @ {result.base_branch})
                </span>
              </p>
            </div>
            <span className="rounded-full bg-emerald-900/50 px-3 py-1 text-xs font-medium text-emerald-300">
              {result.message ?? 'task plan generated'}
            </span>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Orchestration Prompt
              </p>
              <pre className="max-h-64 overflow-auto rounded-md bg-slate-950/80 p-3 text-xs leading-relaxed text-slate-200">
                {result.orchestration_prompt}
              </pre>
            </div>

            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Simple Prompt
              </p>
              <pre className="max-h-64 overflow-auto rounded-md bg-slate-950/80 p-3 text-xs leading-relaxed text-slate-200">
                {result.simple_prompt}
              </pre>
            </div>
          </div>

          {Array.isArray(result.subtask_prompts) && result.subtask_prompts.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Subtask Prompts
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {result.subtask_prompts.map((subtask) => (
                  <div
                    key={subtask.subtask_key || subtask.summary || subtask.prompt}
                    className="rounded-md border border-slate-800 bg-slate-950/60 p-3"
                  >
                    <p className="text-xs font-medium text-slate-200">
                      {subtask.subtask_key || 'Subtask'}
                    </p>
                    {subtask.summary && (
                      <p className="mt-1 text-xs text-slate-400">{subtask.summary}</p>
                    )}
                    <pre className="mt-2 max-h-40 overflow-auto text-xs leading-relaxed text-slate-100">
                      {subtask.prompt}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default CreateTaskPage
