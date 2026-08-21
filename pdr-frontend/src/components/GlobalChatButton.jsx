import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

import { BACKEND_URL as BACKEND } from '../config'

// ── Floating global chat button + modal ──────────────────────────────────────
// No auto-inject. Loan officer types full queries for cross-applicant work:
//   "Compare ntc_001 and msme_002"
//   "How many applicants were rejected?"
//   "Pull up msme_003"

export default function GlobalChatButton() {
  const [open, setOpen]           = useState(false)
  const [messages, setMessages]   = useState([])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 120)
  }, [open])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  async function sendQuery(rawQuery) {
    const trimmed = rawQuery.trim()
    if (!trimmed) return

    setMessages(prev => [...prev, { role: 'user', text: trimmed }])
    setLoading(true)
    setInput('')

    try {
      const res = await axios.post(`${BACKEND}/chatbot/ask`, { query: trimmed })
      setMessages(prev => [...prev, { role: 'analyst', text: res.data.message || '(no response)' }])
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'error', text: 'Could not reach the analyst. Is the backend running on port 8000?' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const EXAMPLES = [
    'Compare ntc_001 and msme_002',
    'How many applicants were rejected?',
    'Pull up msme_003',
    'Show the top 3 riskiest applicants',
  ]

  return (
    <>
      {/* ── Modal backdrop ── */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.35)',
            zIndex: 998,
          }}
        />
      )}

      {/* ── Chat window ── */}
      {open && (
        <div style={{
          position: 'fixed',
          bottom: 90,
          right: 24,
          width: 480,
          maxWidth: 'calc(100vw - 40px)',
          maxHeight: '75vh',
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          background: '#fff',
          borderRadius: 18,
          boxShadow: '0 16px 48px rgba(0,0,0,0.2)',
          border: '1.5px solid #e2e8f0',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            background: '#0f172a',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 18 }}>🤖</span>
              <div>
                <div style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 700 }}>
                  FintrixAi Analyst — Portfolio Mode
                </div>
                <div style={{ color: '#64748b', fontSize: 11, marginTop: 1 }}>
                  Query any applicant · Compare · Portfolio stats
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748b',
                fontSize: 20,
                cursor: 'pointer',
                lineHeight: 1,
                padding: '2px 6px',
              }}
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '14px',
            background: '#fff',
          }}>
            {messages.length === 0 && (
              <div style={{ padding: '8px 0' }}>
                <div style={{ color: '#64748b', fontSize: 13, marginBottom: 14 }}>
                  Ask about any applicant in the database — no need to be on their profile.
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                  Try these
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      onClick={() => sendQuery(ex)}
                      style={{
                        textAlign: 'left',
                        padding: '8px 12px',
                        borderRadius: 8,
                        border: '1px solid #e2e8f0',
                        background: '#f8fafc',
                        color: '#374151',
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#f1f5f9'}
                      onMouseLeave={e => e.currentTarget.style.background = '#f8fafc'}
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} style={{
                marginBottom: 14,
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}>
                <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 3, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {msg.role === 'user' ? 'You' : msg.role === 'error' ? '⚠ Error' : 'Analyst'}
                </div>
                <div style={{
                  maxWidth: '94%',
                  padding: msg.role === 'user' ? '8px 13px' : '12px 14px',
                  borderRadius: msg.role === 'user' ? '13px 13px 3px 13px' : '3px 13px 13px 13px',
                  background: msg.role === 'user' ? '#0f172a' : msg.role === 'error' ? '#fef2f2' : '#f8fafc',
                  color: msg.role === 'user' ? '#f1f5f9' : msg.role === 'error' ? '#991b1b' : '#1e293b',
                  fontSize: msg.role === 'analyst' ? 11.5 : 13,
                  lineHeight: 1.65,
                  whiteSpace: 'pre-wrap',
                  fontFamily: msg.role === 'analyst' ? "'Courier New', Courier, monospace" : 'inherit',
                  border: msg.role === 'analyst' ? '1px solid #e2e8f0' : 'none',
                }}>
                  {msg.text}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ color: '#94a3b8', fontSize: 12, padding: '4px 0' }}>
                ● ● ● Analyst is thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div style={{
            padding: '10px 12px',
            borderTop: '1px solid #e2e8f0',
            background: '#f8fafc',
            display: 'flex',
            gap: 7,
            flexShrink: 0,
          }}>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(input) } }}
              placeholder="Compare ntc_001 and msme_002…"
              disabled={loading}
              style={{
                flex: 1,
                padding: '9px 13px',
                borderRadius: 9,
                border: '1.5px solid #e2e8f0',
                fontSize: 13,
                background: '#fff',
                outline: 'none',
                color: '#0f172a',
              }}
            />
            <button
              onClick={() => sendQuery(input)}
              disabled={loading || !input.trim()}
              style={{
                padding: '9px 18px',
                borderRadius: 9,
                border: 'none',
                background: loading || !input.trim() ? '#e2e8f0' : '#0f172a',
                color: loading || !input.trim() ? '#94a3b8' : '#fff',
                fontSize: 13,
                fontWeight: 700,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Ask →
            </button>
          </div>
        </div>
      )}

      {/* ── Floating trigger button ── */}
      <button
        onClick={() => setOpen(v => !v)}
        title="FintrixAi Credit Analyst"
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 1000,
          width: 56,
          height: 56,
          borderRadius: '50%',
          border: 'none',
          background: open ? '#334155' : '#0f172a',
          color: '#fff',
          fontSize: 24,
          cursor: 'pointer',
          boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background 0.18s, transform 0.18s',
          transform: open ? 'rotate(15deg)' : 'none',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.08)' + (open ? ' rotate(15deg)' : '') }}
        onMouseLeave={e => { e.currentTarget.style.transform = open ? 'rotate(15deg)' : 'none' }}
      >
        {open ? '×' : '🤖'}
      </button>
    </>
  )
}
