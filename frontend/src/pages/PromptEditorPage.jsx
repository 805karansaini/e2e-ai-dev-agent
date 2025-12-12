import { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.BACKEND_URL || 'http://127.0.0.1:8080'

function PromptEditorPage() {
  const [taskId, setTaskId] = useState('')
  const [taskData, setTaskData] = useState(null)
  const [taskPrompt, setTaskPrompt] = useState('')
  const [isTaskLoading, setIsTaskLoading] = useState(false)
  const [isTaskEditing, setIsTaskEditing] = useState(false)
  const [isTaskSaving, setIsTaskSaving] = useState(false)

  const [subTaskId, setSubTaskId] = useState('')
  const [subTaskData, setSubTaskData] = useState(null)
  const [subTaskPrompt, setSubTaskPrompt] = useState('')
  const [isSubTaskLoading, setIsSubTaskLoading] = useState(false)
  const [isSubTaskEditing, setIsSubTaskEditing] = useState(false)
  const [isSubTaskSaving, setIsSubTaskSaving] = useState(false)

  async function handleLoadTask(event) {
    event.preventDefault()

    const trimmedId = taskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a task ID.')
      return
    }

    setIsTaskLoading(true)
    setTaskData(null)
    setTaskPrompt('')
    setIsTaskEditing(false)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setTaskData(data)
      setTaskPrompt(data?.prompt ?? '')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading task:', error)

      let message = 'Failed to load task.'

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

  async function handleSaveTaskPrompt() {
    if (!taskData || !taskId.trim()) return

    const trimmedId = taskId.trim()

    setIsTaskSaving(true)
    try {
      const response = await axios.put(
        `${API_BASE_URL}/db/tasks/${encodeURIComponent(trimmedId)}`,
        { prompt: taskPrompt },
      )
      const data = response?.data?.data ?? null
      setTaskData(data)
      setTaskPrompt(data?.prompt ?? '')
      setIsTaskEditing(false)
      toast.success('Task prompt updated.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error updating task prompt:', error)

      let message = 'Failed to update task prompt.'

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
      setIsTaskSaving(false)
    }
  }

  async function handleLoadSubTask(event) {
    event.preventDefault()

    const trimmedId = subTaskId.trim()
    if (!trimmedId) {
      toast.error('Please enter a sub-task ID.')
      return
    }

    setIsSubTaskLoading(true)
    setSubTaskData(null)
    setSubTaskPrompt('')
    setIsSubTaskEditing(false)

    try {
      const response = await axios.get(
        `${API_BASE_URL}/db/tasks/sub-task/${encodeURIComponent(trimmedId)}`,
      )
      const data = response?.data?.data ?? null
      setSubTaskData(data)
      setSubTaskPrompt(data?.prompt ?? '')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading sub-task:', error)

      let message = 'Failed to load sub-task.'

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

  async function handleSaveSubTaskPrompt() {
    if (!subTaskData || !subTaskId.trim()) return

    const trimmedId = subTaskId.trim()

    setIsSubTaskSaving(true)
    try {
      const response = await axios.put(
        `${API_BASE_URL}/db/tasks/sub-task/${encodeURIComponent(trimmedId)}`,
        { prompt: subTaskPrompt },
      )
      const data = response?.data?.data ?? null
      setSubTaskData(data)
      setSubTaskPrompt(data?.prompt ?? '')
      setIsSubTaskEditing(false)
      toast.success('Sub-task prompt updated.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error updating sub-task prompt:', error)

      let message = 'Failed to update sub-task prompt.'

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
      setIsSubTaskSaving(false)
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-50">Prompt Editor</h2>
        <p className="mt-1 text-sm text-slate-400">
          Load prompts for tasks or subtasks from the database, inspect them, and{' '}
          <span className="font-semibold text-slate-200">double-click</span> to edit
          before saving changes back.
        </p>
      </header>

      {/* Task prompt editor */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Task Prompt</h3>

        <form
          onSubmit={handleLoadTask}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium text-slate-100">Task ID</span>
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="Enter task_id to load"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </label>

          <button
            type="submit"
            disabled={isTaskLoading}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isTaskLoading ? 'Loading…' : 'Load Task'}
          </button>
        </form>

        {taskData && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Task
                </p>
                <p className="text-sm font-medium text-slate-100">
                  {taskData.task_id}{' '}
                  {taskData.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {taskData.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {taskData.status}
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Prompt
                </p>
                <p className="text-[11px] text-slate-500">
                  Double-click the box below to enable editing.
                </p>
              </div>
              <textarea
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                onDoubleClick={() => setIsTaskEditing(true)}
                readOnly={!isTaskEditing}
                placeholder="No prompt stored for this task yet."
                className="min-h-[160px] w-full resize-y rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
              />
              {!isTaskEditing && (
                <p className="text-xs text-slate-500">
                  Prompt is read-only. Double-click inside to switch to edit mode.
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-1">
              <button
                type="button"
                onClick={handleSaveTaskPrompt}
                disabled={!isTaskEditing || isTaskSaving}
                className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isTaskSaving ? 'Saving…' : 'Save Prompt'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Sub-task prompt editor */}
      <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Sub-task Prompt</h3>

        <form
          onSubmit={handleLoadSubTask}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium text-slate-100">Sub-task ID</span>
            <input
              type="text"
              value={subTaskId}
              onChange={(e) => setSubTaskId(e.target.value)}
              placeholder="Enter sub_task_id to load"
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </label>

          <button
            type="submit"
            disabled={isSubTaskLoading}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubTaskLoading ? 'Loading…' : 'Load Sub-task'}
          </button>
        </form>

        {subTaskData && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Sub-task
                </p>
                <p className="text-sm font-medium text-slate-100">
                  {subTaskData.task_id}{' '}
                  {subTaskData.sub_task_id && (
                    <span className="text-slate-500">
                      (sub-task: {subTaskData.sub_task_id})
                    </span>
                  )}
                </p>
              </div>
              <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300">
                Status: {subTaskData.status}
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Prompt
                </p>
                <p className="text-[11px] text-slate-500">
                  Double-click the box below to enable editing.
                </p>
              </div>
              <textarea
                value={subTaskPrompt}
                onChange={(e) => setSubTaskPrompt(e.target.value)}
                onDoubleClick={() => setIsSubTaskEditing(true)}
                readOnly={!isSubTaskEditing}
                placeholder="No prompt stored for this sub-task yet."
                className="min-h-[160px] w-full resize-y rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
              />
              {!isSubTaskEditing && (
                <p className="text-xs text-slate-500">
                  Prompt is read-only. Double-click inside to switch to edit mode.
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-1">
              <button
                type="button"
                onClick={handleSaveSubTaskPrompt}
                disabled={!isSubTaskEditing || isSubTaskSaving}
                className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-slate-50 shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubTaskSaving ? 'Saving…' : 'Save Prompt'}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

export default PromptEditorPage
