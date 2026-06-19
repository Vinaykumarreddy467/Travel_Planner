// ────────────────────────────────────────────────────────
//  🧳 TRAVEL PLANNER — Premium Conversational UI
//  ────────────────────────────────────────────────────────
//  Every detail considered. Every interaction deliberate.
//  A travel companion, not just a chat widget.
// ────────────────────────────────────────────────────────

import React, { useState, useRef, useEffect, useCallback } from 'react'
import 'bootstrap/dist/css/bootstrap.min.css'
import './App.css'

// ─── SVG ICONS ──────────────────────────────────────────
const Icons = {
  Send: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  ),
  Plus: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  Copy: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
}

// ─── SUGGESTIONS DATA ───────────────────────────────────
const SUGGESTIONS = [
  { emoji: '🍣', text: 'Plan 5 days in Tokyo for a foodie' },
  { emoji: '🥐', text: '3 days in Paris on a $1000 budget' },
  { emoji: '🌴', text: 'Best time to visit Bali?' },
  { emoji: '🏛️', text: 'Rome itinerary with family' },
  { emoji: '🎒', text: 'Backpacking SE Asia 2 weeks' },
  { emoji: '🚣', text: 'Romantic weekend in Venice' },
]

// ─── FORMAT TIME ────────────────────────────────────────
function formatTime(date) {
  if (!date) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// ─── RENDER TEXT WITH CLICKABLE LINKS ────────────────────
function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g
  const parts = text.split(urlRegex)
  return parts.map((part, i) => {
    if (part.match(urlRegex)) {
      return (
        <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="text-link">
          {part}
        </a>
      )
    }
    return part
  })
}

// ─── MESSAGE CONTENT RENDERER ───────────────────────────
function MessageContent({ content }) {
  // Split by double newlines for paragraph breaks
  const paragraphs = content.split('\n\n').filter(Boolean)
  
  if (paragraphs.length > 1) {
    return (
      <div className="message-content">
        {paragraphs.map((p, i) => (
          <p key={i}>{linkify(p)}</p>
        ))}
      </div>
    )
  }
  
  // Single block — use line breaks
  return (
    <div className="message-content">
      {content.split('\n').map((line, i) => (
        <React.Fragment key={i}>
          {i > 0 && <br />}
          {linkify(line)}
        </React.Fragment>
      ))}
    </div>
  )
}

// ════════════════════════════════════════════════════════
//  APP
// ════════════════════════════════════════════════════════

export default function App() {
  // ─── STATE ───
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "👋 Hi! I'm your AI Travel Planner. Tell me where you want to go, for how long, and what you're into — I'll help you plan the perfect trip!",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [copiedId, setCopiedId] = useState(null)

  const chatEnd = useRef(null)
  const textareaRef = useRef(null)
  const msgCount = useRef(messages.length)
  const streamContent = useRef('')   // accumulate streaming text

  // ─── AUTO-SCROLL ───
  useEffect(() => {
    if (messages.length > msgCount.current) {
      requestAnimationFrame(() => {
        chatEnd.current?.scrollIntoView({ behavior: 'smooth' })
      })
    }
    msgCount.current = messages.length
  }, [messages])

  // ─── AUTO-RESIZE TEXTAREA ───
  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [])

  useEffect(() => { autoResize() }, [input, autoResize])

  // ─── SSE STREAM READER ───
  async function readSSEStream(response, callbacks) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.chunk) callbacks.onChunk?.(data.chunk)
            if (data.maps) callbacks.onMaps?.(data.maps)
            if (data.done) callbacks.onDone?.()
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  }

  // ─── SEND ───
  async function sendMessage() {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')

    const userMsg = { role: 'user', content: text, timestamp: new Date() }
    const updated = [...messages, userMsg]
    setMessages(updated)
    streamContent.current = ''

    // Add a placeholder streaming message
    const streamingId = Date.now()
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: '', streaming: true, id: streamingId, timestamp: new Date() },
    ])
    setIsStreaming(true)

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: updated.slice(1).map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      if (!res.body) throw new Error('No response body')

      await readSSEStream(res, {
        onChunk: (chunk) => {
          streamContent.current += chunk
          // Update the streaming message with accumulated text
          setMessages(prev => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.streaming) {
              copy[copy.length - 1] = { ...last, content: streamContent.current }
            }
            return copy
          })
        },
        onMaps: (maps) => {
          streamContent.current += `\n\n${maps}`
          setMessages(prev => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.streaming) {
              copy[copy.length - 1] = { ...last, content: streamContent.current }
            }
            return copy
          })
        },
        onDone: () => {
          // Finalize the streaming message
          setMessages(prev => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.streaming) {
              copy[copy.length - 1] = { ...last, streaming: false, content: streamContent.current }
            }
            return copy
          })
          setIsStreaming(false)
        },
      })
    } catch (err) {
      console.error('Stream error:', err)
      setMessages(prev => {
        const copy = [...prev]
        const last = copy[copy.length - 1]
        if (last && last.streaming) {
          copy[copy.length - 1] = {
            ...last,
            streaming: false,
            content: '❌ Could not reach the server. Make sure the backend is running!',
          }
        }
        return copy
      })
      setIsStreaming(false)
    }
  }

  // ─── KEYBOARD ───
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ─── NEW CHAT ───
  function newChat() {
    setMessages([{
      role: 'assistant',
      content: "👋 Hi! I'm your AI Travel Planner. Tell me where you want to go, for how long, and what you're into — I'll help you plan the perfect trip!",
      timestamp: new Date(),
    }])
    setInput('')
    setCopiedId(null)
    setIsStreaming(false)
    streamContent.current = ''
  }

  // ─── COPY ───
  async function copyMessage(content, id) {
    try {
      await navigator.clipboard.writeText(content)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = content
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // ─── DERIVED ───
  const showWelcome = messages.length === 1 && messages[0].role === 'assistant'

  // ══════════════════════════════════════════════════════
  //  RENDER
  // ══════════════════════════════════════════════════════

  return (
    <div className="app">

      {/* ─── HEADER ─── */}
      <header className="header">
        <div className="header-brand">
          <div className="header-icon">🧳</div>
          <div>
            <span className="header-title">Travel Planner</span>
            <span className="header-badge">AI</span>
          </div>
        </div>
        <button className="btn-new-chat" onClick={newChat} title="Start a new conversation">
          <Icons.Plus /> New Chat
        </button>
      </header>

      {/* ─── CHAT AREA ─── */}
      <main className="chat-area">

        {/* WELCOME SCREEN */}
        {showWelcome && (
          <div className="welcome">
            <div className="welcome-icon">🌍</div>
            <h2>Where to next?</h2>
            <p className="welcome-sub">
              Tell me your destination, budget, and style — I'll craft the perfect trip for you.
            </p>

            <div className="suggestion-grid">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-card"
                  onClick={() => {
                    setInput(s.text)
                    textareaRef.current?.focus()
                  }}
                >
                  <span className="emoji">{s.emoji}</span>
                  {s.text}
                </button>
              ))}
            </div>

            <span className="welcome-hint">or type your own question below ✨</span>
          </div>
        )}

        {/* MESSAGES */}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`message ${msg.role === 'user' ? 'message-user' : 'message-ai'}`}
            style={{ animationDelay: `${i * 0.04}s` }}
          >
            <div className="message-avatar">
              {msg.role === 'assistant' ? '🤖' : '👤'}
            </div>

            <div className={`message-bubble ${msg.streaming ? 'is-streaming' : ''}`}>
              <div className="message-header">
                <span className="message-header-name">
                  {msg.role === 'assistant' ? 'Travel Planner' : 'You'}
                </span>
                <span className="message-time">{formatTime(msg.timestamp)}</span>
                {msg.streaming && <span className="streaming-badge">streaming</span>}
              </div>

              {msg.content ? (
                <MessageContent content={msg.content} />
              ) : (
                <div className="streaming-placeholder">
                  <span className="thinking-dot" />
                  <span className="thinking-dot" />
                  <span className="thinking-dot" />
                </div>
              )}

              {msg.role === 'assistant' && !msg.streaming && (
                <button
                  className="copy-btn"
                  onClick={() => copyMessage(msg.content, i)}
                >
                  {copiedId === i ? <Icons.Check /> : <Icons.Copy />}
                  {copiedId === i ? ' Copied' : ' Copy'}
                </button>
              )}
            </div>
          </div>
        ))}

        {/* STREAMING CURSOR — tiny blink at the end of an in-progress message */}
        {isStreaming && (
          <div className="streaming-cursor" />
        )}

        <div ref={chatEnd} className="chat-spacer" />
      </main>

      {/* ─── INPUT AREA ─── */}
      <footer className="input-area">
        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Where are you heading?"
              rows={1}
              disabled={isStreaming}
            />
            <button
              className="send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || isStreaming}
              aria-label="Send message"
            >
              <Icons.Send />
            </button>
          </div>

          <div className="input-footer">
            <span className="input-hint">
              <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for new line
            </span>
          </div>
        </div>
      </footer>

    </div>
  )
}
