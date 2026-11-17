import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'

import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import './styles/global.css'
import './styles/pages.css'

// Static hosts like GitHub Pages have no file at /teach, so a refresh there is a 404.
// VITE_HASH_ROUTER=true (set in .env.production) uses /#/teach URLs instead, which
// always load index.html. Dev keeps clean path URLs.
const useHash = import.meta.env.VITE_HASH_ROUTER === 'true'
const routerFuture = { v7_startTransition: true, v7_relativeSplatPath: true }

// Old path-style links (e.g. /yes_officer/teach) still land on 404.html; move them to the hash form.
if (useHash) {
  const base = import.meta.env.BASE_URL
  const { pathname, search, hash } = window.location
  if (!hash && pathname.startsWith(base) && pathname !== base) {
    window.history.replaceState(null, '', `${base}#/${pathname.slice(base.length)}${search}`)
  }
}

const Router = ({ children }) =>
  useHash ? (
    <HashRouter future={routerFuture}>{children}</HashRouter>
  ) : (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')} future={routerFuture}>
      {children}
    </BrowserRouter>
  )

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </Router>
  </StrictMode>,
)
