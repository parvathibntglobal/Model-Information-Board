import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import './styles/fonts.css'
import './styles/app.css'
import App from './App'

// The single-file build has no server to rewrite paths, so it routes on the hash.
const Router = import.meta.env.VITE_HASH_ROUTER ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router>
      <App />
    </Router>
  </StrictMode>
)
