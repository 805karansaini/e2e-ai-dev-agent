import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layout/MainLayout'
import HomePage from './pages/HomePage'
import CreateTaskPage from './pages/CreateTaskPage'
import PromptEditorPage from './pages/PromptEditorPage'
import StatusViewerPage from './pages/StatusViewerPage'
import SummaryViewerPage from './pages/SummaryViewerPage'

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="/create-task" element={<CreateTaskPage />} />
        <Route path="/prompt-editor" element={<PromptEditorPage />} />
        <Route path="/status" element={<StatusViewerPage />} />
        <Route path="/summary" element={<SummaryViewerPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
