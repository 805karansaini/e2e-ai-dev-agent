import { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.BACKEND_URL || 'http://127.0.0.1:8080'

function StatusViewerPage() {
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState(null)
  const [isTaskLoading, setIsTaskLoading] = useState(false)

  const [subTaskId, setSubTaskId] = useState('')
  const [subTaskStatus, setSubTaskStatus] = useState(null)
  const [isSubTaskLoading, setIsSubTaskLoading] = useState(false)

  async function handleLoadTaskStatus(event) {
    event.preventDefault()

    const trimmedId = taskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a task ID.')
      return
    }

    setIsTaskLoading(true)
    setTaskStatus(null)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setTaskStatus(data)
    } catch (error) {
      // Log full error for debugging
      // eslint-disable-next-line no-console
      console.error('Error loading task status:', error)

      let message = 'Failed to load task status.'

      if (error.response) {
        // Backend returned an error response
        message =
          error.response.data?.message ||
          error.response.data?.detail ||
          message
      } else if (error.request) {
        // Request was sent but no response received (network / CORS / wrong port)
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

  async function handleLoadSubTaskStatus(event) {
    event.preventDefault()

    const trimmedId = subTaskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a sub-task ID.')
      return
    }

    setIsSubTaskLoading(true)
    setSubTaskStatus(null)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/sub-task/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setSubTaskStatus(data)
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading sub-task status:', error)

      let message = 'Failed to load sub-task status.'

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
        <h2 className="text-lg font-semibold text-slate-50">Status</h2>
        <p className="mt-1 text-sm text-slate-400">
          Enter a task or sub-task ID to fetch its latest status from the database.
        </p>
      </header>

      {/* Task status */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Task Status</h3>

        <form
          onSubmit={handleLoadTaskStatus}
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
            {isTaskLoading ? 'Loading…' : 'Get Status'}
          </button>
        </form>

        {taskStatus && (
          <div className="space-y-2 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Task</p>
                <p className="text-sm font-medium text-slate-100">
                  {taskStatus.task_id}{' '}
                  {taskStatus.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {taskStatus.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {taskStatus.status}
              </span>
            </div>

            {taskStatus.summary && (
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-300">Summary: </span>
                {taskStatus.summary}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Sub-task status */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Sub-task Status</h3>

        <form
          onSubmit={handleLoadSubTaskStatus}
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
            {isSubTaskLoading ? 'Loading…' : 'Get Status'}
          </button>
        </form>

        {subTaskStatus && (
          <div className="space-y-2 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Sub-task
                </p>
                <p className="text-sm font-medium text-slate-100">
                  {subTaskStatus.task_id}{' '}
                  {subTaskStatus.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {subTaskStatus.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {subTaskStatus.status}
              </span>
            </div>

            {subTaskStatus.summary && (
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-300">Summary: </span>
                {subTaskStatus.summary}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export default StatusViewerPage
