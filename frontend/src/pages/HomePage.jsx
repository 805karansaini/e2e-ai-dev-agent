import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.BACKEND_URL ||
  'http://127.0.0.1:8080'

const STATUS_OPTIONS = [
  { value: 'PENDING', label: 'In Progress' },
  { value: 'SUCCESS', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
]

function getStatusStyles(status) {
  const normalized = String(status || '').toUpperCase()

  if (normalized === 'SUCCESS') {
    return {
      label: 'completed',
      className:
        'inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-200 dark:ring-emerald-500/25',
    }
  }

  if (normalized === 'FAILED') {
    return {
      label: 'failed',
      className:
        'inline-flex items-center rounded-full bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-100 dark:bg-rose-500/15 dark:text-rose-200 dark:ring-rose-500/30',
    }
  }

  // Default / pending
  return {
    label: 'pending',
    className:
      'inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-100 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-500/30',
  }
}

function getTaskTypeLabel(taskType, isSubTask) {
  const normalized = String(taskType || '').toUpperCase()
  if (normalized === 'SUBTASK' || isSubTask) return 'subtask'
  return 'task'
}

function groupTasks(tasks) {
  const groups = new Map()

  for (const task of tasks) {
    const key = task.task_id || `task-${task.id}`
    if (!groups.has(key)) {
      groups.set(key, { taskId: key, parent: null, subtasks: [] })
    }

    const group = groups.get(key)
    if (task.sub_task_id) {
      group.subtasks.push(task)
    } else {
      group.parent = task
    }
  }

  // Convert map to array, ensuring deterministic order by created_at desc / id desc
  return Array.from(groups.values()).sort((a, b) => {
    const aTime = a.parent?.created_at ?? a.subtasks[0]?.created_at ?? ''
    const bTime = b.parent?.created_at ?? b.subtasks[0]?.created_at ?? ''
    return String(bTime).localeCompare(String(aTime))
  })
}

function TaskRow({ task, isSubtask = false, onEdit, onAddSubtask }) {
  const statusStyles = getStatusStyles(task.status)
  const typeLabel = getTaskTypeLabel(task.task_type, isSubtask)

  return (
    <div
      className={`grid grid-cols-[minmax(80px,0.15fr)_minmax(0,2.2fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.9fr)] items-center gap-4 border-t border-slate-100 bg-white px-5 py-4 text-sm last:border-b sm:px-7 dark:border-slate-800 dark:bg-slate-900/70 my-1 ${isSubtask ? 'pl-6 sm:pl-10' : ''}`}
    >
      {/* Task ID */}
      <div className="flex items-center gap-2 text-xs font-mono font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-sm min-w-0 overflow-hidden">
        {isSubtask && (
          <span className="h-px w-4 rounded-full bg-slate-200 sm:w-5 dark:bg-slate-700 shrink-0" aria-hidden="true" />
        )}
        <span
          className={`${isSubtask ? 'text-slate-700 dark:text-slate-300' : 'text-slate-900 dark:text-white'} truncate`}
        >
          {task.sub_task_id || task.task_id}
        </span>
      </div>

      {/* Description + helper text */}
      <div className="space-y-1 my-1 ml-4 min-w-0">
        <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-50">
          {task.description || 'Untitled task'}
        </p>
        <p className="line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
          {task.summary || task.agent_summary || 'No additional context yet.'}
        </p>
      </div>

      {/* Status */}
      <div className="flex justify-start my-1">
        <span className={statusStyles.className}>{statusStyles.label}</span>
      </div>

      {/* Type */}
      <div className="my-1">
        <span className="inline-flex items-center rounded-full bg-slate-50 px-3 py-1 text-xs font-medium capitalize text-slate-700 ring-1 ring-inset ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700">
          {typeLabel.toLowerCase()}
        </span>
      </div>

      {/* Branch */}
      <div className="text-xs font-medium text-slate-700 dark:text-slate-300 my-1">
        {task.base_branch || '–'}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-1.5">
        {!isSubtask && (
          <button
            type="button"
            onClick={() => onAddSubtask?.(task)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-xs text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
            title="Add sub-task"
          >
            +
          </button>
        )}
        <button
          type="button"
          onClick={() => onEdit?.(task, isSubtask)}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-xs text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
          title="Edit"
        >
          ✎
        </button>
        <button
          type="button"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-[11px] text-slate-700 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
          title="Plan"
        >
          Plan
        </button>
      </div>
    </div>
  )
}

function CreateTaskModal({ open, onClose, isSubtask, parentTask, onCreate }) {
  const [taskId, setTaskId] = useState('')
  const [subTaskId, setSubTaskId] = useState('')
  const [status, setStatus] = useState('PENDING')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [agentSummary, setAgentSummary] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [baseBranch, setBaseBranch] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!open) return

    setTaskId(parentTask?.task_id || '')
    setSubTaskId('')
    setStatus('PENDING')
    setDescription('')
    setPrompt('')
    setAgentSummary('')
    setRepoUrl(parentTask?.repo_url || '')
    setBaseBranch(parentTask?.base_branch || '')
  }, [open, parentTask])

  if (!open) {
    return null
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!taskId) {
      toast.error('Task ID is required.')
      return
    }

    if (isSubtask && !subTaskId) {
      toast.error('Sub-task ID is required.')
      return
    }

    try {
      setIsSaving(true)
      await onCreate({
        isSubtask,
        payload: {
          task_id: taskId,
          ...(isSubtask ? { sub_task_id: subTaskId } : {}),
          description,
          prompt,
          agent_summary: agentSummary,
          repo_url: repoUrl,
          base_branch: baseBranch,
          status,
        },
      })
      onClose()
    } catch {
      // Error surfaced via toast in caller
    } finally {
      setIsSaving(false)
    }
  }

  const heading = isSubtask ? 'New Sub-task' : 'New Task'
  const helperText = isSubtask
    ? 'Create a sub-task linked to an existing task ID.'
    : 'Create a standalone task to track in the database.'

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-4 py-8"
      aria-modal="true"
      role="dialog"
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl bg-white shadow-xl transition-colors dark:border dark:border-slate-800 dark:bg-slate-900"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 transition-colors sm:px-6 dark:border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white sm:text-lg">
              {heading}
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-300 sm:text-sm">
              {helperText}
            </p>
            {isSubtask && parentTask?.task_id && (
              <p className="mt-1 text-xs font-medium text-slate-700 dark:text-slate-200">
                Parent Task ID: <span className="font-mono">{parentTask.task_id}</span>
              </p>
            )}
          </div>

          <div className="h-8 w-8" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          {isSubtask ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-900 dark:text-slate-100">Task ID</span>
                  <input
                    type="text"
                    value={taskId}
                    readOnly
                    className="input-base bg-slate-50/80 font-mono text-xs sm:text-sm dark:bg-slate-800/70"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-900 dark:text-slate-100">Sub Task ID</span>
                  <input
                    type="text"
                    value={subTaskId}
                    onChange={(event) => setSubTaskId(event.target.value)}
                    placeholder="SUB-TASK-001"
                    className="input-base font-mono text-xs sm:text-sm"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-900 dark:text-slate-100">Description</span>
                <input
                  type="text"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Short description of the sub-task"
                  className="input-base"
                />
              </label>

              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-900 dark:text-slate-100">Prompt</span>
                <textarea
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="Create a secure authentication system with JWT tokens…"
                  className="min-h-[120px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
                />
              </label>
            </>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-900 dark:text-slate-100">Task ID</span>
                  <input
                    type="text"
                    value={taskId}
                    onChange={(event) => setTaskId(event.target.value)}
                    placeholder="TASK-001"
                    className="input-base font-mono text-xs sm:text-sm"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-900 dark:text-slate-100">Repository URL</span>
                  <input
                    type="text"
                    value={repoUrl}
                    onChange={(event) => setRepoUrl(event.target.value)}
                    placeholder="https://github.com/example/repo"
                    className="input-base"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-900 dark:text-slate-100">Base Branch</span>
                  <input
                    type="text"
                    value={baseBranch}
                    onChange={(event) => setBaseBranch(event.target.value)}
                    placeholder="main"
                    className="input-base"
                  />
                </label>
              </div>
            </>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="btn-ghost min-w-[96px]"
            >
              Cancel
            </button>
            <button type="submit" disabled={isSaving} className="btn-primary min-w-[130px]">
              {isSaving ? 'Creating…' : heading}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditTaskModal({ open, onClose, task, isSubtask, onSave }) {
  const [status, setStatus] = useState('PENDING')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [agentSummary, setAgentSummary] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [baseBranch, setBaseBranch] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!open || !task) return

    setStatus(task.status || 'PENDING')
    setDescription(task.description || '')
    setPrompt(task.prompt || '')
    setAgentSummary(task.agent_summary || '')
    setRepoUrl(task.repo_url || '')
    setBaseBranch(task.base_branch || '')
  }, [open, task])

  if (!open || !task) {
    return null
  }

  async function handleSubmit(event) {
    event.preventDefault()

    try {
      setIsSaving(true)
      await onSave({
        isSubtask,
        task,
        payload: {
          description,
          prompt,
          agent_summary: agentSummary,
          repo_url: repoUrl,
          base_branch: baseBranch,
          status,
        },
      })
      onClose()
    } catch {
      // Errors are surfaced via toast in the caller
    } finally {
      setIsSaving(false)
    }
  }

  const displayId = isSubtask ? task.sub_task_id : task.task_id

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-4 py-8"
      aria-modal="true"
      role="dialog"
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl bg-white shadow-xl transition-colors dark:border dark:border-slate-800 dark:bg-slate-900"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 transition-colors sm:px-6 dark:border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white sm:text-lg">
              Edit Task
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-300 sm:text-sm">
              Update task details and prompt.
            </p>
          </div>

          <div className="h-8 w-8" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-900 dark:text-slate-100">Task ID</span>
              <input
                type="text"
                value={displayId || ''}
                readOnly
                className="input-base bg-slate-50/80 font-mono text-xs sm:text-sm dark:bg-slate-800/70"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-900 dark:text-slate-100">Status</span>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="input-base cursor-pointer bg-white dark:bg-slate-900"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Description</span>
            <input
              type="text"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Short description of the task"
              className="input-base"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Prompt</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Create a secure authentication system with JWT tokens…"
              className="min-h-[120px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Agent Summary</span>
            <textarea
              value={agentSummary}
              onChange={(event) => setAgentSummary(event.target.value)}
              placeholder="High-level notes on the agent's progress or findings."
              className="min-h-[96px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-900 dark:text-slate-100">Repository URL</span>
              <input
                type="text"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/example/repo"
                className="input-base"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-900 dark:text-slate-100">Base Branch</span>
              <input
                type="text"
                value={baseBranch}
                onChange={(event) => setBaseBranch(event.target.value)}
                placeholder="main"
                className="input-base"
              />
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="btn-ghost min-w-[96px]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="btn-primary min-w-[130px]"
            >
              {isSaving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function HomePage() {
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [expanded, setExpanded] = useState(() => new Set())
  const [editing, setEditing] = useState(null)
  const [createModal, setCreateModal] = useState({
    open: false,
    isSubtask: false,
    parentTask: null,
  })

  const loadTasks = async () => {
    setIsLoading(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/db/tasks`, {
        params: { limit: 200 },
      })
      const data = response?.data?.data
      setTasks(Array.isArray(data?.tasks) ? data.tasks : [])
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading tasks list:', error)
      toast.error('Unable to load tasks from the database.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [])

  const groupedTasks = useMemo(() => groupTasks(tasks), [tasks])

  function toggleExpanded(taskId) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  function handleEditClick(task, isSubtask) {
    setEditing({ task, isSubtask })
  }

  function handleCloseEdit() {
    setEditing(null)
  }

  function handleOpenCreateTask() {
    setCreateModal({ open: true, isSubtask: false, parentTask: null })
  }

  function handleOpenCreateSubtask(task) {
    setCreateModal({ open: true, isSubtask: true, parentTask: task || null })
  }

  function handleCloseCreate() {
    setCreateModal({ open: false, isSubtask: false, parentTask: null })
  }

  function buildErrorMessage(error, fallback) {
    if (error?.response) {
      return (
        error.response.data?.message ||
        error.response.data?.detail ||
        fallback
      )
    }

    if (error?.request) {
      return 'No response from API. Please verify the backend is running and reachable.'
    }

    if (error?.message) {
      return error.message
    }

    return fallback
  }

  async function handleSaveEdit({ isSubtask, task, payload }) {
    const identifier = isSubtask ? task.sub_task_id : task.task_id

    if (!identifier) {
      toast.error('Missing task identifier.')
      throw new Error('Missing task identifier')
    }

    try {
      const endpoint = isSubtask
        ? `/db/tasks/sub-task/${encodeURIComponent(identifier)}`
        : `/db/tasks/${encodeURIComponent(identifier)}`

      const response = await axios.put(`${API_BASE_URL}${endpoint}`, payload)
      const updated = response?.data?.data

      if (!updated) {
        throw new Error('No updated task returned from API.')
      }

      await loadTasks()
      toast.success('Task updated.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error updating task:', error)

      const message = buildErrorMessage(error, 'Failed to update task.')
      toast.error(message)
      throw error
    }
  }

  async function handleCreateTask({ isSubtask, payload }) {
    try {
      const endpoint = isSubtask ? '/db/tasks/sub-task' : '/db/tasks'
      await axios.post(`${API_BASE_URL}${endpoint}`, payload)
      await loadTasks()
      toast.success(isSubtask ? 'Sub-task created.' : 'Task created.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error creating task:', error)

      const message = buildErrorMessage(
        error,
        isSubtask ? 'Failed to create sub-task.' : 'Failed to create task.'
      )
      toast.error(message)
      throw error
    }
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Task Console
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-300">
            Manage and execute development tasks. View high-level tasks alongside their subtasks,
            current status, and branching information.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleOpenCreateTask}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-indigo-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:from-primary-soft hover:to-indigo-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-sm leading-none">
              +
            </span>
            <span>New Task</span>
          </button>
        </div>
      </header>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900/70">
        <div className="flex items-center border-b border-slate-100 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500 transition-colors sm:px-7 dark:border-slate-800 dark:text-slate-300">
          <div className="flex flex-1 items-center gap-3">
            <div className="w-[68px] shrink-0" aria-hidden="true" />
            <div className="grid flex-1 grid-cols-[minmax(80px,0.15fr)_minmax(0,2.2fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.9fr)] items-center gap-4">
              <span className="whitespace-nowrap">Task ID</span>
              <span className="ml-4">Description</span>
              <span>Status</span>
              <span>Type</span>
              <span>Branch</span>
              <span className="text-right">Actions</span>
            </div>
          </div>
        </div>

        <div className="max-h-[520px] overflow-auto">
          <div className="min-w-[720px]">
            {isLoading && (
              <div className="flex items-center justify-center border-t border-slate-100 bg-slate-50 px-4 py-6 text-sm text-slate-500 transition-colors sm:px-6 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300">
                Loading tasks…
              </div>
            )}

            {!isLoading && groupedTasks.length === 0 && (
              <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-4 py-6 text-sm text-slate-500 transition-colors sm:px-6 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300">
                <span className="dark:text-slate-200">No tasks found yet.</span>
                <span className="text-xs">
                  Use the <span className="font-medium text-slate-700 dark:text-slate-200">Create Task</span> page to
                  add your first task.
                </span>
              </div>
            )}

            {!isLoading &&
              groupedTasks.map((group) => {
                const parent = group.parent
                const subtasks = group.subtasks || []
                const isExpanded = expanded.has(group.taskId)

                // If we only have subtasks and no parent, treat the first subtask as the "parent" row visually.
                const mainTask = parent || subtasks[0]

                return (
                  <div key={group.taskId} className="border-t border-slate-100 last:border-b dark:border-slate-800 my-1">
                    <div className="flex items-stretch bg-slate-50/60 transition-colors hover:bg-slate-50 dark:bg-slate-900/40 dark:hover:bg-slate-900/30">
                      <button
                        type="button"
                        onClick={() => toggleExpanded(group.taskId)}
                        className="flex w-[68px] items-center justify-center border-r border-slate-100 px-3 text-slate-500 transition-colors hover:text-slate-700 dark:border-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
                        aria-label={isExpanded ? 'Collapse subtasks' : 'Expand subtasks'}
                      >
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-xs font-medium transition-colors dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
                          {isExpanded ? '–' : '+'}
                        </span>
                      </button>

                      <div className="flex-1">
                        <TaskRow
                          task={mainTask}
                          isSubtask={false}
                          onEdit={handleEditClick}
                          onAddSubtask={handleOpenCreateSubtask}
                        />
                      </div>
                    </div>

                    {isExpanded &&
                      subtasks.map((subtask) => (
                        <TaskRow
                          key={subtask.id}
                          task={subtask}
                          isSubtask
                          onEdit={handleEditClick}
                        />
                      ))}
                  </div>
                )
              })}
          </div>
        </div>
      </div>

      <CreateTaskModal
        open={createModal.open}
        onClose={handleCloseCreate}
        isSubtask={createModal.isSubtask}
        parentTask={createModal.parentTask}
        onCreate={handleCreateTask}
      />

      <EditTaskModal
        open={Boolean(editing)}
        onClose={handleCloseEdit}
        task={editing?.task || null}
        isSubtask={editing?.isSubtask ?? false}
        onSave={handleSaveEdit}
      />
    </section>
  )
}

export default HomePage


