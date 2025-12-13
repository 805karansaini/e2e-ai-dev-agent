import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import './styles/index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#020617',
            color: '#e5e7eb',
            borderRadius: '0.75rem',
            border: '1px solid rgba(30,64,175,0.65)',
          },
        }}
      />
    </BrowserRouter>
  </StrictMode>,
)
