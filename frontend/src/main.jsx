// ──────────────────────────────────────
// ENTRY POINT — React starts here
// ──────────────────────────────────────
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// Mount the App component inside the <div id="root"> in index.html
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
