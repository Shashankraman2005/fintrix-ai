import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

import { BACKEND_URL as BACKEND } from '../config'

export default function ChatPanel({ applicantId, applicantName, decision, isDark = false }) {
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [allApplicants, setAll]       = useState([])
  const [compareOpen, setCompareOpen] = useState(false)
  const [ollamaStatus, setOllamaInfo]  = useState({ online: true, active_model: 'llama3:latest', available_models: ['llama3:latest'] })
  const bottomRef    = useRef(null)
  const compareRef   = useRef(null)

  // Load all applicants and Ollama status
  useEffect(() => {
    axios.get(`${BACKEND}/chatbot/search?limit=20`)
      .then(r => setAll(r.data.results || []))
      .catch(() => {})
    
    axios.get(`${BACKEND}/chatbot/ollama/status`)
      .then(r => setOllamaInfo(r.data))
      .catch(() => {})
  }, [])

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Close compare dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (compareRef.current && !compareRef.current.contains(e.target)) {
        setCompareOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Dynamic quick actions based on the current decision
  const isRejected = (decision || '').toUpperCase().includes('REJECT')
  const quickActions = [
    {
      label: isRejected ? 'Why rejected?' : 'Why approved?',
      query: isRejected
        ? 'Why was this applicant rejected?'
        : 'Why was this applicant approved?',
    },
    { label: 'Biggest risk',    query: 'What is the biggest risk for this applicant?' },
    { label: 'What to change?', query: 'What would this applicant need to change to qualify?' },
    { label: 'Decision letter', query: 'Generate a decision letter for this applicant' },
  ]

  // Only auto-inject applicant ID if the query doesn't already name one
  const hasIdInText = (text) => /\b(ntc|msme|app|user)[_-]?\d/i.test(text)

  async function sendQuery(rawQuery) {
    const trimmed = rawQuery.trim()
    if (!trimmed) return

    const query = hasIdInText(trimmed)
      ? trimmed
      : `${applicantId} — ${trimmed}`

    setMessages(prev => [...prev, { role: 'user', text: trimmed }])
    setLoading(true)
    setInput('')

    try {
      const res = await axios.post(`${BACKEND}/chatbot/ask`, { query })
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

  function handleCompare(otherId) {
    setCompareOpen(false)
    sendQuery(`Compare ${applicantId} and ${otherId}`)
  }

  return (
    <div style={{
      marginTop: 48,
      border: `1.5px solid ${isDark ? '#334155' : '#e2e8f0'}`,
      borderRadius: 16,
      overflow: 'visible',
      boxShadow: isDark ? '0 2px 12px rgba(0,0,0,0.5)' : '0 2px 12px rgba(0,0,0,0.07)',
    }}>
      {/* ── Header ── */}
      <div style={{
        background: '#0f172a',
        padding: '16px 20px',
        borderRadius: '14px 14px 0 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 20 }}>🤖</span>
          <div>
            <div style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 700 }}>
              FintrixAi Credit Analyst
            </div>
            <div style={{ color: '#64748b', fontSize: 11, marginTop: 1 }}>
              Context loaded: {applicantName} · {(applicantId || '').toUpperCase()}
            </div>
          </div>
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          background: 'rgba(99, 102, 241, 0.15)',
          padding: '4px 10px',
          borderRadius: 20,
          border: '1px solid rgba(99, 102, 241, 0.3)',
          fontSize: 11,
          color: '#a5b4fc',
          fontWeight: 600,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: ollamaStatus.online ? '#10b981' : '#f59e0b' }} />
          🦙 Ollama · {ollamaStatus.active_model}
        </div>
      </div>

      {/* ── Quick actions + Compare ── */}
      <div style={{
        padding: '10px 16px',
        background: isDark ? '#1e293b' : '#f8fafc',
        borderBottom: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
        display: 'flex',
        flexWrap: 'wrap',
        gap: 7,
        alignItems: 'center',
      }}>
        {quickActions.map((qa, i) => (
          <button
            key={i}
            disabled={loading}
            onClick={() => sendQuery(qa.query)}
            style={{
              padding: '5px 13px',
              borderRadius: 20,
              border: `1.5px solid ${isDark ? '#475569' : '#e2e8f0'}`,
              background: isDark ? '#0f172a' : '#fff',
              color: isDark ? '#cbd5e1' : '#374151',
              fontSize: 12,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.5 : 1,
              transition: 'background 0.12s',
            }}
            onMouseEnter={e => { if (!loading) e.currentTarget.style.background = isDark ? '#334155' : '#f1f5f9' }}
            onMouseLeave={e => { e.currentTarget.style.background = isDark ? '#0f172a' : '#fff' }}
          >
            {qa.label}
          </button>
        ))}

        {/* Compare dropdown */}
        <div ref={compareRef} style={{ position: 'relative' }}>
          <button
            disabled={loading}
            onClick={() => setCompareOpen(v => !v)}
            style={{
              padding: '5px 13px',
              borderRadius: 20,
              border: '1.5px solid #6366f1',
              background: compareOpen ? '#6366f1' : (isDark ? '#0f172a' : '#fff'),
              color: compareOpen ? '#fff' : '#6366f1',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Compare with ▼
          </button>

          {compareOpen && allApplicants.length > 0 && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 6px)',
              left: 0,
              zIndex: 200,
              background: isDark ? '#1e293b' : '#fff',
              border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
              borderRadius: 12,
              boxShadow: isDark ? '0 8px 28px rgba(0,0,0,0.5)' : '0 8px 28px rgba(0,0,0,0.13)',
              minWidth: 240,
            }}>
              <div style={{ padding: '8px 14px 6px', fontSize: 11, color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Select applicant to compare
              </div>
              {allApplicants
                .filter(a => a.applicant_id !== applicantId)
                .map((a, i, arr) => (
                  <button
                    key={a.applicant_id}
                    onClick={() => handleCompare(a.applicant_id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '9px 14px',
                      border: 'none',
                      borderBottom: i < arr.length - 1 ? `1px solid ${isDark ? '#334155' : '#f1f5f9'}` : 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = isDark ? '#0f172a' : '#f8fafc'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: isDark ? '#f8fafc' : '#0f172a' }}>
                      {a.name}
                    </span>
                    <span style={{
                      fontSize: 11,
                      color: a.grade === 'E' || a.grade === 'D' ? (isDark ? '#f87171' : '#991b1b') : a.grade === 'A' || a.grade === 'B' ? (isDark ? '#4ade80' : '#166534') : (isDark ? '#fbbf24' : '#92400e'),
                      fontWeight: 700,
                      marginLeft: 10,
                    }}>
                      Grade {a.grade}
                    </span>
                  </button>
                ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Message thread ── */}
      <div style={{
        minHeight: 80,
        maxHeight: 460,
        overflowY: 'auto',
        padding: '16px',
        background: isDark ? '#1e293b' : '#fff',
      }}>
        {messages.length === 0 && (
          <div style={{ color: '#94a3b8', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
            Ask a question about <strong>{applicantName}</strong> using quick actions above,
            <br />or type your own question below.
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: 16,
            display: 'flex',
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 3, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {msg.role === 'user' ? 'Loan Officer' : msg.role === 'error' ? '⚠ Error' : 'Analyst'}
            </div>
            <div style={{
              maxWidth: '92%',
              padding: msg.role === 'user' ? '9px 14px' : '14px 16px',
              borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '4px 14px 14px 14px',
              background: msg.role === 'user' ? (isDark ? '#3b82f6' : '#0f172a') : msg.role === 'error' ? (isDark ? 'rgba(153, 27, 27, 0.2)' : '#fef2f2') : (isDark ? '#334155' : '#f8fafc'),
              color: msg.role === 'user' ? '#f1f5f9' : msg.role === 'error' ? (isDark ? '#f87171' : '#991b1b') : (isDark ? '#f8fafc' : '#1e293b'),
              fontSize: msg.role === 'analyst' ? 12 : 13,
              lineHeight: 1.65,
              whiteSpace: 'pre-wrap',
              fontFamily: msg.role === 'analyst' ? "'Courier New', Courier, monospace" : 'inherit',
              border: msg.role === 'analyst' ? `1px solid ${isDark ? '#475569' : '#e2e8f0'}` : 'none',
            }}>
              {msg.text}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#94a3b8', fontSize: 12, padding: '4px 0' }}>
            <span style={{ display: 'inline-block', animation: 'pulse 1.2s ease-in-out infinite' }}>●</span>
            <span style={{ animation: 'pulse 1.2s ease-in-out infinite 0.2s' }}>●</span>
            <span style={{ animation: 'pulse 1.2s ease-in-out infinite 0.4s' }}>●</span>
            <span style={{ marginLeft: 4 }}>Analyst is thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div style={{
        padding: '12px 14px',
        borderTop: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
        background: isDark ? '#0f172a' : '#f8fafc',
        borderRadius: '0 0 14px 14px',
        display: 'flex',
        gap: 8,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(input) } }}
          placeholder={`Ask about ${applicantName}…  (Enter to send)`}
          disabled={loading}
          style={{
            flex: 1,
            padding: '10px 14px',
            borderRadius: 10,
            border: `1.5px solid ${isDark ? '#334155' : '#e2e8f0'}`,
            fontSize: 13,
            background: isDark ? '#1e293b' : '#fff',
            outline: 'none',
            color: isDark ? '#f8fafc' : '#0f172a',
          }}
        />
        <button
          onClick={() => sendQuery(input)}
          disabled={loading || !input.trim()}
          style={{
            padding: '10px 22px',
            borderRadius: 10,
            border: 'none',
            background: loading || !input.trim() ? (isDark ? '#334155' : '#e2e8f0') : (isDark ? '#f8fafc' : '#0f172a'),
            color: loading || !input.trim() ? '#94a3b8' : (isDark ? '#0f172a' : '#fff'),
            fontSize: 13,
            fontWeight: 700,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
            whiteSpace: 'nowrap',
          }}
        >
          Ask →
        </button>
      </div>
    </div>
  )
}
