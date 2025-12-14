"use client"

import { Fragment, useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PlayCircle, Zap, Cpu, Plus, Edit, ChevronRight, ChevronDown, Loader2 } from "lucide-react"
import {
  autoTask,
  createSubTask,
  createTask,
  importTaskFromJira,
  listTasks,
  orchestrateTask,
  startTask,
  updateSubTaskRecord,
  updateTaskRecord,
  type TaskRecord,
  type AttachmentPath,
} from "@/lib/api"

interface Task {
  id: string | number
  task_id: string
  sub_task_id: string | null
  task_type: string
  description: string
  repo_url: string | null
  base_branch: string | null
  status:
    | "PENDING"
    | "PLANNING"
    | "READY"
    | "QUEUED"
    | "IN_PROGRESS"
    | "REVIEWING"
    | "PULL_REQUEST"
    | "DONE"
    | "FAILURE"
  prompt: string
  summary: string | null
  agent_summary: string | null
  jira_task_id?: string | null
  subtasks?: Task[]
  attachment_path?: AttachmentPath[] | null
  additional_json?: Record<string, unknown> | null
  created_at?: string
  updated_at?: string
}

function normalizeTasks(records: TaskRecord[]): Task[] {
  const byId = new Map<string, Task>()

  const ensureParent = (rec: TaskRecord) => {
    const key = rec.task_id
    if (!byId.has(key)) {
      byId.set(key, {
        id: rec.id,
        task_id: rec.task_id,
        sub_task_id: null,
        task_type: "TASK",
        description: rec.description ?? "",
        repo_url: rec.repo_url ?? null,
        base_branch: rec.base_branch ?? null,
        status: rec.status,
        prompt: rec.prompt ?? "",
        summary: rec.summary ?? null,
        agent_summary: rec.agent_summary ?? null,
        jira_task_id: rec.task_id,
        attachment_path: rec.attachment_path ?? null,
        additional_json: rec.additional_json ?? null,
        subtasks: [],
        created_at: rec.created_at,
        updated_at: rec.updated_at,
      })
    }
    return byId.get(key)!
  }

  for (const rec of records) {
    if (rec.task_type === "TASK" && !rec.sub_task_id) {
      byId.set(rec.task_id, {
        id: rec.id,
        task_id: rec.task_id,
        sub_task_id: null,
        task_type: rec.task_type,
        description: rec.description ?? "",
        repo_url: rec.repo_url ?? null,
        base_branch: rec.base_branch ?? null,
        status: rec.status,
        prompt: rec.prompt ?? "",
        summary: rec.summary ?? null,
        agent_summary: rec.agent_summary ?? null,
        jira_task_id: rec.task_id,
        attachment_path: rec.attachment_path ?? null,
        additional_json: rec.additional_json ?? null,
        subtasks: [],
      })
      continue
    }

    // Subtasks or tasks without parent present
    const parent = ensureParent(rec)
    parent.subtasks = parent.subtasks || []
    parent.subtasks.push({
      id: rec.id,
      task_id: rec.task_id,
      sub_task_id: rec.sub_task_id || rec.task_id,
      task_type: rec.task_type,
      description: rec.description ?? "",
      repo_url: rec.repo_url ?? null,
      base_branch: rec.base_branch ?? null,
      status: rec.status,
      prompt: rec.prompt ?? "",
      summary: rec.summary ?? null,
      agent_summary: rec.agent_summary ?? null,
      jira_task_id: rec.sub_task_id,
      attachment_path: rec.attachment_path ?? null,
      additional_json: rec.additional_json ?? null,
      subtasks: [],
      created_at: rec.created_at,
      updated_at: rec.updated_at,
    })
  }

  return Array.from(byId.values()).sort((a, b) =>
    String(b.id ?? "").localeCompare(String(a.id ?? "")),
  )
}

export default function TaskManagementPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [expandedTasks, setExpandedTasks] = useState<Set<string | number>>(new Set())
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<"edit" | "new" | "subtask" | "jira" | "view">("edit")
  const [parentTaskId, setParentTaskId] = useState<string | null>(null)
  const [viewingTask, setViewingTask] = useState<Task | null>(null)
  const [isViewModalOpen, setIsViewModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null)
  const EXPANDED_STORAGE_KEY = "task-expanded-ids"
  const POLL_MS = 5000

  const loadTasks = useCallback(async () => {
    setError(null)
    try {
      const records = await listTasks()
      setTasks(normalizeTasks(records))
    } catch (err) {
      console.error("Failed to load tasks", err)
      setError(err instanceof Error ? err.message : "Unable to load tasks")
    }
  }, [])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(EXPANDED_STORAGE_KEY) : null
    if (stored) {
      try {
        const ids = JSON.parse(stored) as Array<string | number>
        setExpandedTasks(new Set(ids))
      } catch {
        /* ignore parse errors */
      }
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify(Array.from(expandedTasks)))
  }, [expandedTasks])

  useEffect(() => {
    const id = setInterval(() => {
      void loadTasks()
    }, POLL_MS)
    return () => clearInterval(id)
  }, [loadTasks])

  const handleNewTask = () => {
    setEditingTask({
      id: Date.now().toString(),
      task_id: `TASK-${String(tasks.length + 1).padStart(3, "0")}`,
      sub_task_id: null,
      task_type: "TASK",
      description: "",
      repo_url: "",
      base_branch: "main",
      status: "PENDING",
      prompt: "",
      summary: null,
      agent_summary: null,
    })
    setModalMode("new")
    setIsModalOpen(true)
  }

  const handleAddSubtask = (parentTask: Task) => {
    const subtaskCount = parentTask.subtasks?.length || 0
    setEditingTask({
      id: Date.now().toString(),
      task_id: parentTask.task_id,
      sub_task_id: `SUB-${String(subtaskCount + 1).padStart(3, "0")}`,
      task_type: "SUBTASK",
      description: "",
      repo_url: null,
      base_branch: null,
      status: "PENDING",
      prompt: "",
      summary: null,
      agent_summary: null,
    })
    // Parent ids can come back as numbers from the API; store as string for state consistency
    setParentTaskId(String(parentTask.id))
    setModalMode("subtask")
    setIsModalOpen(true)
  }

  const handleEdit = (task: Task) => {
    setEditingTask({ ...task })
    setModalMode("edit")
    setIsModalOpen(true)
  }

  const handleJiraImport = () => {
    setEditingTask({
      id: Date.now().toString(),
      task_id: "",
      sub_task_id: null,
      task_type: "TASK",
      description: "",
      repo_url: "",
      base_branch: "",
      status: "PENDING",
      prompt: "",
      summary: null,
      agent_summary: null,
      jira_task_id: "",
    })
    setModalMode("jira")
    setIsModalOpen(true)
  }

  const handleViewTask = (task: Task) => {
    setViewingTask(task)
    setIsViewModalOpen(true)
  }

  const handleSave = async () => {
    if (!editingTask) return

    try {
      if (modalMode === "jira") {
        await importTaskFromJira({
          jira_task_id: editingTask.jira_task_id || editingTask.task_id,
          repo_url: editingTask.repo_url || "",
          branch: editingTask.base_branch || "main",
        })
      } else if (modalMode === "new") {
        await createTask({
          task_id: editingTask.task_id,
          description: editingTask.description,
          summary: editingTask.summary || undefined,
          repo_url: editingTask.repo_url || undefined,
          base_branch: editingTask.base_branch || undefined,
          status: editingTask.status,
          prompt: editingTask.prompt,
          agent_summary: editingTask.agent_summary || undefined,
        })
      } else if (modalMode === "subtask" && parentTaskId) {
        await createSubTask({
          task_id: editingTask.task_id || parentTaskId,
          sub_task_id: editingTask.sub_task_id || "",
          description: editingTask.description,
          summary: editingTask.summary || undefined,
          repo_url: editingTask.repo_url || undefined,
          base_branch: editingTask.base_branch || undefined,
          status: editingTask.status,
          prompt: editingTask.prompt,
          agent_summary: editingTask.agent_summary || undefined,
        })
      } else {
        // edit existing
        if (editingTask.sub_task_id) {
          await updateSubTaskRecord(editingTask.sub_task_id, {
            description: editingTask.description,
            summary: editingTask.summary || undefined,
            repo_url: editingTask.repo_url || undefined,
            base_branch: editingTask.base_branch || undefined,
            status: editingTask.status,
            prompt: editingTask.prompt,
            agent_summary: editingTask.agent_summary || undefined,
          })
        } else {
          await updateTaskRecord(editingTask.task_id, {
            description: editingTask.description,
            summary: editingTask.summary || undefined,
            repo_url: editingTask.repo_url || undefined,
            base_branch: editingTask.base_branch || undefined,
            status: editingTask.status,
            prompt: editingTask.prompt,
            agent_summary: editingTask.agent_summary || undefined,
          })
        }
      }
      await loadTasks()
      setIsModalOpen(false)
      setEditingTask(null)
      setParentTaskId(null)
    } catch (err) {
      console.error("Save failed", err)
      setError(err instanceof Error ? err.message : "Save failed")
    }
  }

  const handleAction = async (task: Task, action: "plan" | "develop" | "auto-develop") => {
    if (!task.task_id && !task.sub_task_id) return
    if (!task.repo_url) {
      setError("Repository URL is required to run tasks.")
      return
    }

    const payload = {
      task_id: task.sub_task_id || task.task_id,
      repo_url: task.repo_url || "",
      base_branch: task.base_branch || "main",
    }
    const key = `${task.sub_task_id || task.task_id}-${action}`

    try {
      setError(null)
      setActionLoadingKey(key)
      if (action === "plan") {
        await orchestrateTask(payload)
      } else if (action === "develop") {
        await startTask(payload)
      } else {
        await autoTask(payload)
      }
      await loadTasks()
    } catch (error) {
      console.error(`Action ${action} failed`, error)
      setError(error instanceof Error ? error.message : "Action failed")
    } finally {
      setActionLoadingKey((prev) => (prev === key ? null : prev))
    }
  }

  const toggleExpand = (taskId: string | number) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const getStatusColor = (status: string) => {
    const normalized = (status || "").toUpperCase()
    switch (normalized) {
      case "DONE":
        return "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
      case "IN_PROGRESS":
        return "bg-blue-500/10 text-blue-700 border-blue-500/20"
      case "PENDING":
        return "bg-amber-500/10 text-amber-700 border-amber-500/20"
      case "FAILURE":
        return "bg-red-500/10 text-red-700 border-red-500/20"
      case "PLANNING":
        return "bg-yellow-500/10 text-yellow-700 border-yellow-500/20"
      case "READY":
        return "bg-green-500/10 text-green-700 border-green-500/20"
      case "QUEUED":
        return "bg-gray-500/10 text-gray-700 border-gray-500/20"
      case "REVIEWING":
        return "bg-orange-500/10 text-orange-700 border-orange-500/20"
      case "PULL_REQUEST":
        return "bg-pink-500/10 text-pink-700 border-pink-500/20"
      default:
        return "bg-gray-500/10 text-gray-700 border-gray-500/20"
    }
  }

  const renderTaskRow = (task: Task, isSubtask = false) => (
    <Fragment key={`${isSubtask ? "sub" : "task"}-${task.id}-${task.sub_task_id || task.task_id}`}>
      <TableRow
        key={task.id}
        className={`${isSubtask ? "bg-muted/30" : ""} hover:bg-muted/50 transition-colors`}
      >
        <TableCell
          className="font-mono text-sm cursor-pointer"
          onDoubleClick={() => handleViewTask(task)}
        >
          <div className="flex items-center gap-2">
            {!isSubtask && task.subtasks && task.subtasks.length > 0 && (
              <button
                onClick={() => toggleExpand(task.id)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {expandedTasks.has(task.id) ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
            )}
            {isSubtask && <span className="ml-6" />}
            <span className="font-semibold">{task.sub_task_id || task.task_id}</span>
          </div>
        </TableCell>
        <TableCell onDoubleClick={() => handleViewTask(task)} className="cursor-pointer">
          <div className="max-w-md min-w-0 space-y-1">
            <p className="truncate text-sm font-semibold text-foreground">
              {task.summary || task.description || "Untitled task"}
            </p>
            {task.description && task.summary && (
              <p className="truncate text-xs text-muted-foreground">
                {task.description}
              </p>
            )}
          </div>
        </TableCell>
        <TableCell>
          <Badge variant="outline" className={getStatusColor(task.status)}>
            {task.status.replace("_", " ")}
          </Badge>
        </TableCell>
        <TableCell>
          <Badge variant="secondary" className="text-xs">
            {task.task_type}
          </Badge>
        </TableCell>
        <TableCell className="font-mono text-xs text-muted-foreground">{task.base_branch || "-"}</TableCell>
        <TableCell>
          <div className="flex items-center gap-1">
            {!isSubtask && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAddSubtask(task)}
                className="h-8 w-8 p-0"
                title="Add Subtask"
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => handleEdit(task)} className="h-8 w-8 p-0">
              <Edit className="h-3.5 w-3.5" />
            </Button>
            {(["plan", "develop", "auto-develop"] as const).map((action) => {
              const key = `${task.sub_task_id || task.task_id}-${action}`
              const loading = actionLoadingKey === key
              const Icon = action === "plan" ? PlayCircle : action === "develop" ? Cpu : Zap
              const label = action === "plan" ? "Plan" : action === "develop" ? "Develop" : "Auto"
              return (
                <Button
                  key={action}
                  size="sm"
                  variant="outline"
                  disabled={loading}
                  onClick={() => handleAction(task, action)}
                  className={`h-8 px-2 text-xs gap-1 ${loading ? "cursor-wait opacity-80" : ""}`}
                >
                  {loading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                  {label}
                </Button>
              )
            })}
          </div>
        </TableCell>
      </TableRow>
      {!isSubtask && task.subtasks && expandedTasks.has(task.id) &&
        task.subtasks.map((subtask) => renderTaskRow(subtask, true))}
    </Fragment>
  )

  const handleBackToParentTask = () => {
    if (!viewingTask || !viewingTask.sub_task_id) return

    // Find parent task
    const parentTask = tasks.find((task) => task.task_id === viewingTask.task_id && !task.sub_task_id)
    if (parentTask) {
      setViewingTask(parentTask)
    }
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-[1600px] space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Task Management</h1>
            <p className="text-muted-foreground mt-1">Manage and execute development tasks</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" className="gap-2 bg-transparent" onClick={handleJiraImport}>
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm.5 17.5l-5-5 1.5-1.5 3.5 3.5 6.5-6.5 1.5 1.5-8 8z" />
              </svg>
              Import from Jira
            </Button>
            <Button className="gap-2" onClick={handleNewTask}>
              <Plus className="h-4 w-4" />
              New Task
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[140px]">Task ID</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-[120px]">Status</TableHead>
                <TableHead className="w-[100px]">Type</TableHead>
                <TableHead className="w-[120px]">Branch</TableHead>
                <TableHead className="w-[320px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>{tasks.map((task) => renderTaskRow(task))}</TableBody>
          </Table>
        </div>

        {/* View Modal */}
        <Dialog open={isViewModalOpen} onOpenChange={setIsViewModalOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                {viewingTask?.sub_task_id && (
                  <Button variant="ghost" size="sm" onClick={handleBackToParentTask} className="h-8 w-8 p-0">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="m15 18-6-6 6-6" />
                    </svg>
                  </Button>
                )}
                <span>{viewingTask?.sub_task_id ? "Subtask Details" : "Task Details"}</span>
              </DialogTitle>
            </DialogHeader>

            {viewingTask && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Task ID</Label>
                    <p className="font-mono font-semibold text-lg">{viewingTask.sub_task_id || viewingTask.task_id}</p>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Status</Label>
                    <Badge
                      variant="outline"
                      className={`${getStatusColor(viewingTask.status)} w-fit text-sm px-3 py-1`}
                    >
                      {viewingTask.status.replace("_", " ")}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase tracking-wider">Task Type</Label>
                  <Badge variant="secondary" className="w-fit">
                    {viewingTask.task_type}
                  </Badge>
                </div>

                {/* Jira-specific information section */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="text-blue-600"
                    >
                      <rect width="18" height="18" x="3" y="3" rx="2" />
                      <path d="M8 7v7" />
                      <path d="M12 7v4" />
                      <path d="M16 7v9" />
                    </svg>
                    Jira Information
                  </h3>

                  {viewingTask.jira_task_id && (
                    <div className="space-y-2">
                      <Label className="text-muted-foreground text-xs uppercase tracking-wider">Jira Task ID</Label>
                      <p className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                        {viewingTask.jira_task_id}
                      </p>
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                      Jira Issue Title / Summary
                    </Label>
                    <p className="text-base leading-relaxed bg-blue-500/5 border border-blue-500/20 p-4 rounded-md">
                      {viewingTask.summary || <span className="text-muted-foreground italic">No summary provided</span>}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Jira Description</Label>
                    <p className="text-base leading-relaxed bg-blue-500/5 border border-blue-500/20 p-4 rounded-md">
                      {viewingTask.description || (
                        <span className="text-muted-foreground italic">No description provided</span>
                      )}
                    </p>
                  </div>

                  {Array.isArray(viewingTask.attachment_path) && viewingTask.attachment_path.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-muted-foreground text-xs uppercase tracking-wider">Jira Attachments</Label>
                      <ul className="space-y-1 rounded-md border border-blue-500/20 bg-blue-500/5 p-3 text-sm text-blue-700 dark:text-blue-300">
                        {viewingTask.attachment_path.map((att, idx) => (
                          <li key={`${att.path || att.filename || idx}`}>
                            {att.path ? (
                              <a
                                href={att.path}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:underline break-all"
                              >
                                {att.filename || att.path}
                              </a>
                            ) : (
                              <span className="break-all">{att.filename}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Agent-specific information section */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="text-purple-600"
                    >
                      <path d="M12 8V4H8" />
                      <rect width="16" height="12" x="4" y="8" rx="2" />
                      <path d="M2 14h2" />
                      <path d="M20 14h2" />
                      <path d="M15 13v2" />
                      <path d="M9 13v2" />
                    </svg>
                    Agent Information
                  </h3>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Agent Prompt</Label>
                    <div className="bg-purple-500/5 border border-purple-500/20 p-4 rounded-md font-mono text-sm leading-relaxed whitespace-pre-wrap">
                      {viewingTask.prompt || <span className="text-muted-foreground italic">No prompt provided</span>}
                    </div>
                  </div>

                  {viewingTask.agent_summary && (
                    <div className="space-y-2">
                      <Label className="text-muted-foreground text-xs uppercase tracking-wider">Agent Summary</Label>
                      <div className="bg-purple-500/5 border border-purple-500/20 p-4 rounded-md text-sm leading-relaxed">
                        <p className="text-purple-700 dark:text-purple-300">{viewingTask.agent_summary}</p>
                      </div>
                    </div>
                  )}

                  {viewingTask.additional_json && (
                    <div className="space-y-2">
                      <Label className="text-muted-foreground text-xs uppercase tracking-wider">Additional JSON</Label>
                      <pre className="bg-purple-500/5 border border-purple-500/20 p-4 rounded-md font-mono text-xs leading-relaxed overflow-x-auto">
                        {JSON.stringify(viewingTask.additional_json, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-6 border-t pt-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Repository URL</Label>
                    {viewingTask.repo_url ? (
                      <a
                        href={viewingTask.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline block truncate"
                      >
                        {viewingTask.repo_url}
                      </a>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">Not specified</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">Base Branch</Label>
                    <p className="font-mono text-sm">
                      {viewingTask.base_branch || <span className="text-muted-foreground italic">Not specified</span>}
                    </p>
                  </div>
                </div>

                {viewingTask.subtasks && viewingTask.subtasks.length > 0 && (
                  <div className="space-y-2 border-t pt-4">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                      Subtasks ({viewingTask.subtasks.length})
                    </Label>
                    <div className="space-y-2">
                      {viewingTask.subtasks.map((subtask) => (
                        <div
                          key={subtask.id}
                          className="flex items-center justify-between p-3 bg-muted/30 rounded-md border hover:bg-muted/50 transition-colors cursor-pointer"
                          onClick={() => handleViewTask(subtask)}
                        >
                          <div className="flex-1">
                            <p className="font-medium text-sm">{subtask.description}</p>
                            <p className="text-xs text-muted-foreground mt-1">ID: {subtask.sub_task_id}</p>
                          </div>
                          <Badge variant="outline" className={`${getStatusColor(subtask.status)} text-xs`}>
                            {subtask.status.replace("_", " ")}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setIsViewModalOpen(false)}>
                Close
              </Button>
              <Button
                onClick={() => {
                  if (viewingTask) {
                    setIsViewModalOpen(false)
                    handleEdit(viewingTask)
                  }
                }}
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit Task
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {modalMode === "new"
                  ? "New Task"
                  : modalMode === "subtask"
                    ? "Add Subtask"
                    : modalMode === "jira"
                      ? "Import Task from Jira"
                      : "Edit Task"}
              </DialogTitle>
              <DialogDescription>
                {modalMode === "new"
                  ? "Create a new task"
                  : modalMode === "subtask"
                    ? "Add a subtask to the parent task"
                    : modalMode === "jira"
                      ? "Import a task from Jira by providing task details"
                      : "Update task details and prompt"}
              </DialogDescription>
            </DialogHeader>

            {editingTask && (
              <div className="space-y-4">
                {modalMode === "jira" ? (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="jira-task-id">Jira Task ID *</Label>
                      <Input
                        id="jira-task-id"
                        value={editingTask.jira_task_id || ""}
                        onChange={(e) => setEditingTask({ ...editingTask, jira_task_id: e.target.value })}
                        placeholder="e.g., PROJ-123"
                        className="font-mono"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="repo-url-jira">Repository URL *</Label>
                      <Input
                        id="repo-url-jira"
                        value={editingTask.repo_url || ""}
                        onChange={(e) => setEditingTask({ ...editingTask, repo_url: e.target.value })}
                        placeholder="https://github.com/example/repo"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="branch-jira">Branch *</Label>
                      <Input
                        id="branch-jira"
                        value={editingTask.base_branch || ""}
                        onChange={(e) => setEditingTask({ ...editingTask, base_branch: e.target.value })}
                        placeholder="main"
                        required
                      />
                    </div>

                    <div className="rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
                      The task will be automatically fetched from Jira and created with the provided repository
                      settings.
                    </div>
                  </>
                ) : (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="jira-summary">Jira Issue Title/Summary</Label>
                      <Input
                        id="jira-summary"
                        value={editingTask.summary || ""}
                        onChange={(e) => setEditingTask({ ...editingTask, summary: e.target.value })}
                        placeholder="Brief summary of the issue"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="jira-description">Jira Description</Label>
                      <Textarea
                        id="jira-description"
                        value={editingTask.description}
                        onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
                        className="min-h-[100px]"
                        placeholder="Detailed description from Jira"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="agent-prompt">Agent Prompt</Label>
                      <Textarea
                        id="agent-prompt"
                        value={editingTask.prompt}
                        onChange={(e) => setEditingTask({ ...editingTask, prompt: e.target.value })}
                        className="min-h-[120px] font-mono text-sm"
                        placeholder="Enter instructions for the agent..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="repo-url">Repository URL</Label>
                        <Input
                          id="repo-url"
                          value={editingTask.repo_url || ""}
                          onChange={(e) => setEditingTask({ ...editingTask, repo_url: e.target.value })}
                          placeholder="https://github.com/..."
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="branch">Base Branch</Label>
                        <Input
                          id="branch"
                          value={editingTask.base_branch || ""}
                          onChange={(e) => setEditingTask({ ...editingTask, base_branch: e.target.value })}
                          placeholder="main"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="status">Status</Label>
                      <select
                        id="status"
                        value={editingTask.status}
                        onChange={(e) =>
                          setEditingTask({
                            ...editingTask,
                            status: e.target.value as Task["status"],
                          })
                        }
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="PENDING">PENDING</option>
                        <option value="PLANNING">PLANNING</option>
                        <option value="READY">READY</option>
                        <option value="QUEUED">QUEUED</option>
                        <option value="IN_PROGRESS">IN_PROGRESS</option>
                        <option value="REVIEWING">REVIEWING</option>
                        <option value="PULL_REQUEST">PULL_REQUEST</option>
                        <option value="DONE">DONE</option>
                        <option value="FAILURE">FAILURE</option>
                      </select>
                    </div>

                    {/* Read-only fields for reference */}
                    <div className="rounded-md border border-muted bg-muted/20 p-3 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Read-Only Information</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Task ID:</span>
                          <span className="ml-2 font-mono">{editingTask.sub_task_id || editingTask.task_id}</span>
                        </div>
                        {editingTask.agent_summary && (
                          <div className="col-span-2">
                            <span className="text-muted-foreground">Agent Summary:</span>
                            <p className="ml-2 mt-1">{editingTask.agent_summary}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave}>
                {modalMode === "jira" ? "Import Task" : modalMode === "edit" ? "Save Changes" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}
