import { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.BACKEND_URL || 'http://127.0.0.1:8080'

function SummaryViewerPage() {
  const [taskId, setTaskId] = useState('')
  const [taskSummary, setTaskSummary] = useState(null)
  const [isTaskLoading, setIsTaskLoading] = useState(false)

  const [subTaskId, setSubTaskId] = useState('')
  const [subTaskSummary, setSubTaskSummary] = useState(null)
  const [isSubTaskLoading, setIsSubTaskLoading] = useState(false)

  async function handleLoadTaskSummary(event) {
    event.preventDefault()

    const trimmedId = taskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a task ID.')
      return
    }

    setIsTaskLoading(true)
    setTaskSummary(null)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setTaskSummary(data)
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading task summary:', error)

      let message = 'Failed to load task summary.'

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
      setIsTaskLoading(false)
    }
  }

  async function handleLoadSubTaskSummary(event) {
    event.preventDefault()

    const trimmedId = subTaskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a sub-task ID.')
      return
    }

    setIsSubTaskLoading(true)
    setSubTaskSummary(null)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/sub-task/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setSubTaskSummary(data)
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading sub-task summary:', error)

      let message = 'Failed to load sub-task summary.'

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
      setIsSubTaskLoading(false)
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-50">Summary</h2>
        <p className="mt-1 text-sm text-slate-400">
          Retrieve high-level summaries and outcomes for tasks and subtasks. The API
          response includes status plus both user-facing and agent-generated
          summaries.
        </p>
      </header>

      {/* Task summary */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Task Summary</h3>

        <form
          onSubmit={handleLoadTaskSummary}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium text-slate-100">Task ID</span>
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="Enter task_id"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </label>

          <button
            type="submit"
            disabled={isTaskLoading}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isTaskLoading ? 'Loading…' : 'Get Summary'}
          </button>
        </form>

        {taskSummary && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Task</p>
                <p className="text-sm font-medium text-slate-100">
                  {taskSummary.task_id}{' '}
                  {taskSummary.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {taskSummary.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {taskSummary.status}
              </span>
            </div>

            {taskSummary.summary && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Summary
                </p>
                <p className="mt-1 text-sm text-slate-200">{taskSummary.summary}</p>
              </div>
            )}

            {taskSummary.agent_summary && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Agent Summary
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  {taskSummary.agent_summary}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sub-task summary */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Sub-task Summary</h3>

        <form
          onSubmit={handleLoadSubTaskSummary}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium text-slate-100">
              Sub-task ID
            </span>
            <input
              type="text"
              value={subTaskId}
              onChange={(e) => setSubTaskId(e.target.value)}
              placeholder="Enter sub_task_id"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </label>

          <button
            type="submit"
            disabled={isSubTaskLoading}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubTaskLoading ? 'Loading…' : 'Get Summary'}
          </button>
        </form>

        {subTaskSummary && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Sub-task
                </p>
                <p className="text-sm font-medium text-slate-100">
                  {subTaskSummary.task_id}{' '}
                  {subTaskSummary.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {subTaskSummary.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {subTaskSummary.status}
              </span>
            </div>

            {subTaskSummary.summary && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Summary
                </p>
                <p className="mt-1 text-sm text-slate-200">
                  {subTaskSummary.summary}
                </p>
              </div>
            )}

            {subTaskSummary.agent_summary && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Agent Summary
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  {subTaskSummary.agent_summary}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export default SummaryViewerPage
