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

// Icon components
function PlusIcon({ className }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  )
}

function EditIcon({ className }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
      />
    </svg>
  )
}

function TaskRow({ task, isSubtask = false, onEdit, onAddSubtask, onPlan, onAuto, onDevelopment }) {
  const statusStyles = getStatusStyles(task.status)
  const typeLabel = getTaskTypeLabel(task.task_type, isSubtask)

  return (
    <div
      className={`grid grid-cols-[minmax(80px,0.15fr)_minmax(0,2.2fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.9fr)] items-center gap-4 border-t border-slate-100 bg-white px-5 py-4 text-sm last:border-b sm:px-7 dark:border-slate-800 dark:bg-slate-900/70 ${isSubtask ? 'pl-6 sm:pl-10' : ''}`}
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
      <div className="space-y-1 min-w-0">
        <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-50">
          {task.description || 'Untitled task'}
        </p>
        <p className="line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
          {task.summary || task.agent_summary || 'No additional context yet.'}
        </p>
      </div>

      {/* Status */}
      <div className="flex justify-start">
        <span className={statusStyles.className}>{statusStyles.label}</span>
      </div>

      {/* Type */}
      <div>
        <span className="inline-flex items-center rounded-full bg-slate-50 px-3 py-1 text-xs font-medium capitalize text-slate-700 ring-1 ring-inset ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700">
          {typeLabel.toLowerCase()}
        </span>
      </div>

      {/* Branch */}
      <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
        {task.base_branch || '–'}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-1.5">
        {!isSubtask && (
          <button
            type="button"
            onClick={() => onAddSubtask?.(task)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 transition-colors hover:bg-slate-100 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-600"
            title="Add sub-task"
          >
            <PlusIcon className="h-4 w-4" />
          </button>
        )}
        <button
          type="button"
          onClick={() => onEdit?.(task, isSubtask)}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 transition-colors hover:bg-slate-100 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-600"
          title="Edit"
        >
          <EditIcon className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onPlan?.(task, isSubtask)}
          className="inline-flex h-8 items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-2.5 text-[11px] font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-600"
          title="Plan - Generate and edit prompts"
        >
          Plan
        </button>
        <button
          type="button"
          onClick={() => onAuto?.(task, isSubtask)}
          className="inline-flex h-8 items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-2.5 text-[11px] font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-600"
          title="Auto - Generate prompts and start development"
        >
          Auto
        </button>
        <button
          type="button"
          onClick={() => onDevelopment?.(task, isSubtask)}
          className="inline-flex h-8 items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-2.5 text-[11px] font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-600"
          title="Development - Start development directly"
        >
          Dev
        </button>
      </div>
    </div>
  )
}

function ImportTaskModal({ open, onClose, onImport }) {
  const [jiraTaskId, setJiraTaskId] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [isImporting, setIsImporting] = useState(false)

  useEffect(() => {
    if (!open) return

    setJiraTaskId('')
    setRepoUrl('')
    setBranch('')
  }, [open])

  if (!open) {
    return null
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!jiraTaskId.trim()) {
      toast.error('Jira Task ID is required.')
      return
    }

    if (!repoUrl.trim()) {
      toast.error('Repository URL is required.')
      return
    }

    if (!branch.trim()) {
      toast.error('Branch is required.')
      return
    }

    try {
      setIsImporting(true)
      await onImport({
        jira_task_id: jiraTaskId.trim(),
        repo_url: repoUrl.trim(),
        branch: branch.trim(),
      })
      onClose()
    } catch {
      // Error surfaced via toast in caller
    } finally {
      setIsImporting(false)
    }
  }

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
              Import Task from Jira
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-300 sm:text-sm">
              Import a task from Jira and add it to the database.
            </p>
          </div>

          <div className="h-8 w-8" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Jira Task ID</span>
            <input
              type="text"
              value={jiraTaskId}
              onChange={(event) => setJiraTaskId(event.target.value)}
              placeholder="PROJ-123"
              className="input-base font-mono text-xs sm:text-sm"
              required
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enter the Jira task ID (e.g., PROJ-123)
            </p>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Repository URL</span>
            <input
              type="text"
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              placeholder="https://github.com/example/repo"
              className="input-base"
              required
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Branch</span>
            <input
              type="text"
              value={branch}
              onChange={(event) => setBranch(event.target.value)}
              placeholder="main"
              className="input-base"
              required
            />
          </label>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isImporting}
              className="btn-ghost min-w-[96px]"
            >
              Cancel
            </button>
            <button type="submit" disabled={isImporting} className="btn-primary min-w-[130px]">
              {isImporting ? 'Importing…' : 'Import Task'}
            </button>
          </div>
        </form>
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

function PlanModal({ open, onClose, task, planData, onSave }) {
  const [orchestrationPrompt, setOrchestrationPrompt] = useState('')
  const [simplePrompt, setSimplePrompt] = useState('')
  const [subtaskPrompts, setSubtaskPrompts] = useState([])
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!open || !planData) return

    setOrchestrationPrompt(planData.orchestration_prompt || '')
    setSimplePrompt(planData.simple_prompt || '')
    setSubtaskPrompts(planData.subtask_prompts || [])
  }, [open, planData])

  if (!open || !task || !planData) {
    return null
  }

  async function handleSubmit(event) {
    event.preventDefault()

    try {
      setIsSaving(true)
      await onSave({
        task,
        planData: {
          ...planData,
          orchestration_prompt: orchestrationPrompt,
          simple_prompt: simplePrompt,
          subtask_prompts: subtaskPrompts,
        },
      })
      onClose()
    } catch {
      // Errors are surfaced via toast in the caller
    } finally {
      setIsSaving(false)
    }
  }

  function handleSubtaskPromptChange(index, field, value) {
    const updated = [...subtaskPrompts]
    updated[index] = { ...updated[index], [field]: value }
    setSubtaskPrompts(updated)
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-4 py-8"
      aria-modal="true"
      role="dialog"
    >
      <div
        className="relative w-full max-w-4xl rounded-2xl bg-white shadow-xl transition-colors dark:border dark:border-slate-800 dark:bg-slate-900 max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 transition-colors sm:px-6 dark:border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white sm:text-lg">
              Task Plan - Generated Prompts
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-300 sm:text-sm">
              Review and edit the generated prompts for task: <span className="font-mono">{task.task_id}</span>
            </p>
          </div>

          <div className="h-8 w-8" />
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-5 py-4 sm:px-6 sm:py-5 space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Orchestration Prompt</span>
            <textarea
              value={orchestrationPrompt}
              onChange={(event) => setOrchestrationPrompt(event.target.value)}
              className="min-h-[120px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-900 dark:text-slate-100">Simple Prompt</span>
            <textarea
              value={simplePrompt}
              onChange={(event) => setSimplePrompt(event.target.value)}
              className="min-h-[120px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
            />
          </label>

          {subtaskPrompts.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                Subtask Prompts ({subtaskPrompts.length})
              </h4>
              {subtaskPrompts.map((subtask, index) => (
                <div key={index} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                  <div className="mb-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        Subtask Key:
                      </span>
                      <span className="text-xs font-mono text-slate-900 dark:text-slate-100">
                        {subtask.subtask_key || `Subtask ${index + 1}`}
                      </span>
                    </div>
                    {subtask.summary && (
                      <div>
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Summary: </span>
                        <span className="text-xs text-slate-600 dark:text-slate-400">{subtask.summary}</span>
                      </div>
                    )}
                    {subtask.description && (
                      <div>
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Description: </span>
                        <span className="text-xs text-slate-600 dark:text-slate-400">{subtask.description}</span>
                      </div>
                    )}
                  </div>
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="font-medium text-slate-900 dark:text-slate-100">Prompt</span>
                    <textarea
                      value={subtask.prompt || ''}
                      onChange={(event) => handleSubtaskPromptChange(index, 'prompt', event.target.value)}
                      className="min-h-[100px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500"
                    />
                  </label>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="btn-ghost min-w-[96px]"
            >
              Cancel
            </button>
            <button type="submit" disabled={isSaving} className="btn-primary min-w-[130px]">
              {isSaving ? 'Saving…' : 'Save & Start Development'}
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
  const [planModal, setPlanModal] = useState({
    open: false,
    task: null,
    planData: null,
  })
  const [importModal, setImportModal] = useState({
    open: false,
  })
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

  function handleOpenImportTask() {
    setImportModal({ open: true })
  }

  function handleCloseImport() {
    setImportModal({ open: false })
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

  async function handleImportTask(payload) {
    try {
      const response = await axios.post(`${API_BASE_URL}/db/tasks/import-from-jira`, payload)
      await loadTasks()
      toast.success('Task imported from Jira successfully.')
      return response.data
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error importing task from Jira:', error)

      const message = buildErrorMessage(error, 'Failed to import task from Jira.')
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

  async function handlePlan(task, isSubtask = false) {
    const taskId = isSubtask ? task.sub_task_id : task.task_id
    if (!taskId || !task.repo_url) {
      toast.error('Task ID and Repository URL are required for planning.')
      return
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/tasks/orchestrator`, {
        task_id: taskId,
        repo_url: task.repo_url,
        base_branch: task.base_branch || 'main',
      })

      const planData = response?.data?.data
      if (!planData) {
        throw new Error('No plan data returned from API.')
      }

      setPlanModal({
        open: true,
        task: { ...task, task_id: taskId },
        planData,
      })
      toast.success('Task plan generated successfully.')
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error generating plan:', error)

      const message = buildErrorMessage(error, 'Failed to generate task plan.')
      toast.error(message)
    }
  }

  function handleClosePlan() {
    setPlanModal({ open: false, task: null, planData: null })
  }

  async function handleSavePlan({ task, planData }) {
    // For now, we'll just start development with the saved prompts
    // In the future, you might want to save the edited prompts to the database
    try {
      const isSubtask = !!task.sub_task_id && !task.task_id
      await handleDevelopment(task, isSubtask)
      toast.success('Plan saved and development started.')
    } catch (error) {
      // Error already handled in handleDevelopment
      throw error
    }
  }

  async function handleAuto(task, isSubtask = false) {
    const taskId = isSubtask ? task.sub_task_id : task.task_id
    if (!taskId || !task.repo_url) {
      toast.error('Task ID and Repository URL are required for auto mode.')
      return
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/tasks/auto`, {
        task_id: taskId,
        repo_url: task.repo_url,
        base_branch: task.base_branch || 'main',
      })

      const result = response?.data?.data
      if (!result) {
        throw new Error('No response data returned from API.')
      }

      toast.success(
        `Auto mode started. ${result.started_subtasks?.length || 0} subtask(s) queued for execution.`
      )
      await loadTasks()
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error starting auto mode:', error)

      const message = buildErrorMessage(error, 'Failed to start auto mode.')
      toast.error(message)
    }
  }

  async function handleDevelopment(task, isSubtask = false) {
    const taskId = isSubtask ? task.sub_task_id : task.task_id
    if (!taskId || !task.repo_url) {
      toast.error('Task ID and Repository URL are required for development mode.')
      return
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/tasks/start`, {
        task_id: taskId,
        repo_url: task.repo_url,
        base_branch: task.base_branch || 'main',
      })

      const result = response?.data?.data
      if (!result) {
        throw new Error('No response data returned from API.')
      }

      toast.success(
        `Development started. ${result.started_subtasks?.length || 0} subtask(s) queued for execution.`
      )
      await loadTasks()
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error starting development:', error)

      const message = buildErrorMessage(error, 'Failed to start development. Make sure prompts are generated first.')
      toast.error(message)
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
            onClick={handleOpenImportTask}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-indigo-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:from-primary-soft hover:to-indigo-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-sm leading-none">
              +
            </span>
            <span>Import Task</span>
          </button>
        </div>
      </header>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900/70">
        <div className="flex items-center border-b border-slate-100 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500 transition-colors sm:px-7 dark:border-slate-800 dark:text-slate-300">
          <div className="flex flex-1 items-center gap-3">
            <div className="w-[68px] shrink-0" aria-hidden="true" />
            <div className="grid flex-1 grid-cols-[minmax(80px,0.15fr)_minmax(0,2.2fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.9fr)] items-center gap-4">
              <span className="whitespace-nowrap">Task ID</span>
              <span>Description</span>
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
                          onPlan={handlePlan}
                          onAuto={handleAuto}
                          onDevelopment={handleDevelopment}
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
                          onPlan={handlePlan}
                          onAuto={handleAuto}
                          onDevelopment={handleDevelopment}
                        />
                      ))}
                  </div>
                )
              })}
          </div>
        </div>
      </div>

      <ImportTaskModal
        open={importModal.open}
        onClose={handleCloseImport}
        onImport={handleImportTask}
      />

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

      <PlanModal
        open={planModal.open}
        onClose={handleClosePlan}
        task={planModal.task}
        planData={planModal.planData}
        onSave={handleSavePlan}
      />
    </section>
  )
}

export default HomePage


