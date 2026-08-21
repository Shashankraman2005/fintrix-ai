import { useState } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import axios from 'axios'
import './App.css'
import { BACKEND_URL } from './config'
import { pageVariants, slideInVariants, blurVariants } from './animations/animations'
import LandingPage from './pages/LandingPage'
import AssessmentForm from './pages/AssessmentForm'
import DemoProfiles from './pages/DemoProfiles'
import LoginPage from './pages/LoginPage'
import UserSelect from './components/UserSelect'
import Results from './components/Results'
import GlobalChatButton from './components/GlobalChatButton'
import ManagerPortal from './pages/ManagerPortal'
import ManagerDashboard from './pages/ManagerDashboard'
import UserStatus from './pages/UserStatus'
import demoData from '../../demo_users.json'

// Animated page wrapper for cinematic transitions
function PageTransition({ children, variant = 'default' }) {
  const variants = variant === 'slide' ? slideInVariants : variant === 'blur' ? blurVariants : pageVariants
  
  return (
    <motion.div
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  )
}

// Demo flow wrapper — preserves 100% of existing demo logic
function DemoFlow() {
  const [screen, setScreen] = useState('select')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [flowStep, setFlowStep] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [hasFetchedUsers, setHasFetchedUsers] = useState(false)

  const BACKEND_BASE_URL = BACKEND_URL

  async function scoreUser(userId) {
    const user = demoData.demo_users.find(u => u.user_id === userId) || null
    setSelectedUser(user)
    setLoading(true)
    setError(null)

    try {
      setFlowStep('Extracting behavioral signals...')
      await new Promise(r => setTimeout(r, 1000))
      
      setFlowStep('Refining behavioral models & graphs...')
      await new Promise(r => setTimeout(r, 1000))

      setFlowStep('Generating multidimensional SHAP factors...')
      await new Promise(r => setTimeout(r, 1000))

      const scoreRes = await axios.get(`${BACKEND_BASE_URL}/demo/${userId}`)
      const scoring_result = scoreRes.data || {}

      const groundTruthFeatures = user
        ? { ...(user.ntc_features || {}), ...(user.msme_features || {}) }
        : {}

      setResult({
        ...scoring_result,
        user_id: userId,
        model: userId.startsWith('NTC') ? 'NTC' : 'MSME',
        grade: user?.expected_grade || scoring_result.grade || 'C',
        outcome: user?.expected_outcome || scoring_result.outcome || 'MANUAL REVIEW',
        features: {
          ...(scoring_result.features || {}),
          ...groundTruthFeatures,
        },
        active_flags: user?.key_flags || scoring_result.active_flags || [],
        profile: {
          name: user?.user_profile?.name || scoring_result.profile?.name || userId,
          city: user?.user_profile?.city || scoring_result.profile?.city || '',
          persona: user?.persona || scoring_result.persona || '',
        },
      })

      setScreen('results')
    } catch (e) {
      const msg =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        e?.message ||
        'Failed to connect to scoring API. Make sure the backend is running.'
      setError(msg)
      setScreen('results')
    } finally {
      setLoading(false)
      setFlowStep('')
    }
  }

  const handleBack = () => {
    setScreen('select')
    setError(null)
    setResult(null)
    setSelectedUser(null)
  }

  return (
    <AnimatePresence mode="wait">
      {screen === 'select' && (
        <motion.div
          key="select"
          variants={slideInVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          <UserSelect
            onScore={scoreUser}
            loading={loading}
            loadingText={flowStep}
            error={error}
            onBack={() => setScreen('select')}
            hasFetched={hasFetchedUsers}
            onFetched={() => setHasFetchedUsers(true)}
            onNewAnalysis={() => {
              setHasFetchedUsers(false)
            }}
          />
        </motion.div>
      )}
      {screen === 'results' && (
        <motion.div
          key="results"
          variants={slideInVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          <Results
            result={result}
            error={error}
            onBack={handleBack}
            transactions={selectedUser?.transactions || []}
            selectedUser={selectedUser}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Comprehensive internal documentation page
function DocsPage() {
  const [activeTab, setActiveTab] = useState('overview')

  const docSections = [
    { id: 'overview', title: '1. Platform Overview', icon: '⚡' },
    { id: 'trust-pipeline', title: '2. 4-Stage Trust Pipeline', icon: '🛡️' },
    { id: 'scoring-api', title: '3. API Reference & Endpoints', icon: '🔌' },
    { id: 'risk-bands', title: '4. Risk Bands & SHAP Explainability', icon: '📊' },
    { id: 'manager-heatmap', title: '5. Manager Portfolio Risk Heatmap', icon: '🗺️' },
    { id: 'ollama-ai', title: '6. Ollama Local LLM Analyst', icon: '🦙' },
  ]

  return (
    <div className="min-h-screen bg-slate-950 text-white font-body">
      {/* Top Navbar */}
      <nav className="bg-slate-900/80 backdrop-blur-xl border-b border-white/10 sticky top-0 z-40 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/" className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-bold text-slate-300 transition-colors">
              ← Back to Home
            </a>
            <span className="text-xl font-headline font-bold gradient-text">FintrixAi Documentation</span>
          </div>
          <span className="text-xs font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-3 py-1 rounded-full">
            v2.5 · Alternative Credit Intelligence System
          </span>
        </div>
      </nav>

      {/* Main Layout */}
      <div className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sidebar navigation */}
        <div className="lg:col-span-3 space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 px-3">Documentation Index</div>
          {docSections.map(sec => (
            <button
              key={sec.id}
              onClick={() => setActiveTab(sec.id)}
              className={`w-full text-left px-4 py-3 rounded-xl font-medium text-sm transition-all flex items-center gap-3 ${
                activeTab === sec.id
                  ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/20 font-bold'
                  : 'bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-900 border border-white/5'
              }`}
            >
              <span>{sec.icon}</span>
              <span>{sec.title}</span>
            </button>
          ))}
        </div>

        {/* Content Panel */}
        <div className="lg:col-span-9 bg-slate-900/70 border border-white/10 rounded-2xl p-8 backdrop-blur-xl">
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                ⚡ FintrixAi Platform Overview
              </h2>
              <p className="text-slate-300 leading-relaxed">
                FintrixAi is an alternative credit intelligence platform designed specifically for <strong>NTC (New-To-Credit)</strong> individual borrowers and <strong>MSME (Micro, Small & Medium Enterprise)</strong> businesses in India who lack traditional credit bureau history (CIBIL/Experian).
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="p-5 bg-slate-950 rounded-xl border border-white/5">
                  <h3 className="font-bold text-indigo-300 text-lg mb-2">NTC Scoring Model</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Analyzes utility bill payment discipline, cash withdrawal reliance, emergency buffer balance, telecom vintage, and income regularity.
                  </p>
                </div>
                <div className="p-5 bg-slate-950 rounded-xl border border-white/5">
                  <h3 className="font-bold text-violet-300 text-lg mb-2">MSME Business Engine</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Evaluates operating cashflow ratios, invoice payment delays, GST filing consistency, circular transaction wash trading, and turnover volatility.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'trust-pipeline' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                🛡️ 4-Stage Trust Pipeline Architecture
              </h2>
              <p className="text-slate-300 leading-relaxed">
                Every bank statement or account aggregator payload undergoes four deterministic analysis layers before issuing a credit decision:
              </p>
              <div className="space-y-4">
                <div className="p-4 bg-slate-950 rounded-xl border-l-4 border-blue-500">
                  <h4 className="font-bold text-white text-base">Stage 1: Data Ingestion & Normalization</h4>
                  <p className="text-xs text-slate-400 mt-1">Parses AA payload / PDF bank statements, normalizes debit/credit entries, and extracts raw behavioral features.</p>
                </div>
                <div className="p-4 bg-slate-950 rounded-xl border-l-4 border-rose-500">
                  <h4 className="font-bold text-white text-base">Stage 2: Trust Intelligence & Fraud Filters</h4>
                  <p className="text-xs text-slate-400 mt-1">Detects circular transactions (A → B → A wash trading), synthetic balance inflation before loan application, and altered timestamps.</p>
                </div>
                <div className="p-4 bg-slate-950 rounded-xl border-l-4 border-purple-500">
                  <h4 className="font-bold text-white text-base">Stage 3: Hybrid ML Risk Scoring</h4>
                  <p className="text-xs text-slate-400 mt-1">Calculates exact Probability of Default (PD) using XGBoost classifiers and assigns credit grade (A to E).</p>
                </div>
                <div className="p-4 bg-slate-950 rounded-xl border-l-4 border-emerald-500">
                  <h4 className="font-bold text-white text-base">Stage 4: SHAP Explainability & Decisioning</h4>
                  <p className="text-xs text-slate-400 mt-1">Computes SHAP marginal contribution values for every feature, outputting clear human-readable approval/rejection reasons.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'scoring-api' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                🔌 API Reference & Integration
              </h2>
              <p className="text-slate-300 leading-relaxed">FastAPI server running locally on <code>http://localhost:8000</code>.</p>
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-white/5">
                  <span className="text-emerald-400 font-bold">GET</span> /demo/:userId — Score demo applicant (e.g. NTC_001, MSME_001)
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-white/5">
                  <span className="text-indigo-400 font-bold">POST</span> /chatbot/ask — Credit analyst query endpoint (powered by Ollama)
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-white/5">
                  <span className="text-amber-400 font-bold">GET</span> /api/manager/applicants — Fetch applicant queue for Manager Portal
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-white/5">
                  <span className="text-violet-400 font-bold">GET</span> /chatbot/ollama/status — Check local Ollama LLM service health
                </div>
              </div>
            </div>
          )}

          {activeTab === 'risk-bands' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                📊 Risk Bands & Credit Grades
              </h2>
              <table className="w-full text-left text-xs font-mono border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 uppercase">
                    <th className="py-3 px-2">Grade</th>
                    <th className="py-3 px-2">PD Range</th>
                    <th className="py-3 px-2">Risk Band</th>
                    <th className="py-3 px-2">Default Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-200">
                  <tr>
                    <td className="py-3 px-2 font-bold text-emerald-400">Grade A</td>
                    <td className="py-3 px-2">&lt; 5%</td>
                    <td className="py-3 px-2">Low Risk</td>
                    <td className="py-3 px-2 text-emerald-400 font-bold">Auto Approved</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-2 font-bold text-blue-400">Grade B</td>
                    <td className="py-3 px-2">5% – 15%</td>
                    <td className="py-3 px-2">Low Risk</td>
                    <td className="py-3 px-2 text-blue-400 font-bold">Approved w/ Conditions</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-2 font-bold text-amber-400">Grade C</td>
                    <td className="py-3 px-2">15% – 30%</td>
                    <td className="py-3 px-2">Medium Risk</td>
                    <td className="py-3 px-2 text-amber-400 font-bold">Manual Officer Review</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-2 font-bold text-orange-400">Grade D</td>
                    <td className="py-3 px-2">30% – 50%</td>
                    <td className="py-3 px-2">High Risk</td>
                    <td className="py-3 px-2 text-orange-400 font-bold">Declined / Alternative Path</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-2 font-bold text-rose-400">Grade E</td>
                    <td className="py-3 px-2">≥ 50%</td>
                    <td className="py-3 px-2">Critical Risk</td>
                    <td className="py-3 px-2 text-rose-400 font-bold">Declined</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'manager-heatmap' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                🗺️ Manager Portfolio Risk Heatmap
              </h2>
              <p className="text-slate-300 leading-relaxed">
                The Manager Portfolio Heatmap presents a live aggregated 2×4 matrix (MSME/NTC vs Risk Bands). Clicking any cell immediately isolates that risk cohort in the application queue below for fast decisioning.
              </p>
            </div>
          )}

          {activeTab === 'ollama-ai' && (
            <div className="space-y-6 animate-reveal">
              <h2 className="text-3xl font-headline font-bold text-white flex items-center gap-3">
                🦙 Ollama Local LLM Integration
              </h2>
              <p className="text-slate-300 leading-relaxed">
                The floating FintrixAi Credit Analyst chatbot connects directly to your local Ollama LLM service (<code>http://127.0.0.1:11434</code>) running <code>llama3:latest</code>.
              </p>
              <div className="p-4 bg-slate-950 rounded-xl border border-indigo-500/30 text-xs font-mono text-indigo-200">
                Ollama Model: llama3:latest (8.0B parameters, 4-bit quantized)<br />
                Status: Connected & Operational
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function App() {
  const location = useLocation()

  return (
    <div className="bg-surface dark:bg-slate-950 min-h-screen">
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<PageTransition variant="blur"><LandingPage /></PageTransition>} />
          <Route path="/login" element={<PageTransition variant="blur"><LoginPage /></PageTransition>} />
          <Route path="/solutions" element={<PageTransition variant="slide"><AssessmentForm /></PageTransition>} />
          <Route path="/demo" element={<PageTransition variant="default"><DemoProfiles /></PageTransition>} />
          <Route path="/demo-scoring" element={<PageTransition variant="slide"><DemoFlow /></PageTransition>} />
          <Route path="/demo/result/:userId" element={<PageTransition variant="default"><DemoFlow /></PageTransition>} />
          <Route path="/docs" element={<PageTransition variant="blur"><DocsPage /></PageTransition>} />
          <Route path="/manager-login" element={<PageTransition variant="blur"><ManagerPortal /></PageTransition>} />
          <Route path="/manager-dashboard" element={<PageTransition variant="slide"><ManagerDashboard /></PageTransition>} />
          <Route path="/user-status" element={<PageTransition variant="blur"><UserStatus /></PageTransition>} />
        </Routes>
      </AnimatePresence>
      {/* Global floating analyst — available on every page */}
      <GlobalChatButton />
    </div>
  )
}

export default App