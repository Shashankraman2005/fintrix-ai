import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Search, ArrowLeft, Users, MessageSquare, FileText, Filter, TrendingUp, TrendingDown, Minus, Layers } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { BACKEND_URL } from '../config';

const getRiskBand = (pd) => {
  if (pd < 0.10) return 'low';
  if (pd < 0.25) return 'medium';
  if (pd < 0.50) return 'high';
  return 'critical';
};

const RISK_BANDS = [
  { key: 'low', label: 'Low Risk', pdRange: '< 10% PD', color: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400', activeGlow: 'ring-2 ring-emerald-500 shadow-lg shadow-emerald-500/20' },
  { key: 'medium', label: 'Medium Risk', pdRange: '10–25% PD', color: 'border-amber-500/30 bg-amber-500/10 text-amber-400', activeGlow: 'ring-2 ring-amber-500 shadow-lg shadow-amber-500/20' },
  { key: 'high', label: 'High Risk', pdRange: '25–50% PD', color: 'border-orange-500/30 bg-orange-500/10 text-orange-400', activeGlow: 'ring-2 ring-orange-500 shadow-lg shadow-orange-500/20' },
  { key: 'critical', label: 'Critical Risk', pdRange: '50%+ PD', color: 'border-rose-500/30 bg-rose-500/10 text-rose-400', activeGlow: 'ring-2 ring-rose-500 shadow-lg shadow-rose-500/20' },
];

export default function ManagerDashboard() {
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('NTC'); // NTC or MSME
  const [selectedHeatmapCell, setSelectedHeatmapCell] = useState(null); // { type: 'NTC'|'MSME'|'ALL', riskBand: 'low'|... }
  
  const [selectedApplicant, setSelectedApplicant] = useState(null);
  const [remarks, setRemarks] = useState('');
  const [showStatusModal, setShowStatusModal] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    fetchApplicants();
  }, []);

  const fetchApplicants = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${BACKEND_URL}/api/manager/applicants`);
      setApplicants(res.data || []);
    } catch (err) {
      console.error("Failed to fetch applicants:", err);
      setApplicants([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (actionType) => {
    if (!remarks.trim()) {
      alert("Please provide the officer remarks before approving or declining.");
      return;
    }
    try {
      await axios.put(`${BACKEND_URL}/api/manager/applicant/${selectedApplicant.applicant_id}/status`, {
        outcome: actionType === 'approve' ? 'APPROVED' : 'REJECTED',
        remarks: remarks
      });
      setShowStatusModal(true);
      setTimeout(() => {
        setShowStatusModal(false);
        setSelectedApplicant(null);
        setRemarks('');
        fetchApplicants();
      }, 1500);
    } catch (err) {
      console.error("Action failed:", err);
      alert("Failed to submit action");
    }
  };

  // Build Portfolio Heatmap Matrix
  const heatmapMatrix = useMemo(() => {
    const types = ['NTC', 'MSME'];
    const matrix = {};

    types.forEach(t => {
      matrix[t] = {};
      RISK_BANDS.forEach(b => {
        const matching = applicants.filter(a => {
          const isNTC = a.applicant_id?.toLowerCase().startsWith('ntc');
          const isMSME = a.applicant_id?.toLowerCase().startsWith('msme');
          const matchesType = (t === 'NTC' && isNTC) || (t === 'MSME' && isMSME);
          const matchesBand = getRiskBand(a.default_probability ?? 0) === b.key;
          return matchesType && matchesBand;
        });

        const count = matching.length;
        const avgPD = count > 0 ? matching.reduce((sum, item) => sum + (item.default_probability ?? 0), 0) / count : 0;
        const avgScore = count > 0 ? Math.round(850 - avgPD * 550) : null;

        // Synthetic trend indicator for portfolio intelligence
        let trendIcon = <Minus size={12} className="text-slate-500" />;
        let trendText = 'stable';
        let trendColor = 'text-slate-400';

        if (b.key === 'low' && count > 0) {
          trendIcon = <TrendingDown size={12} className="text-emerald-400" />;
          trendText = '-0.8% PD';
          trendColor = 'text-emerald-400';
        } else if (b.key === 'critical' && count > 0) {
          trendIcon = <TrendingUp size={12} className="text-rose-400" />;
          trendText = '+1.4% PD';
          trendColor = 'text-rose-400';
        }

        matrix[t][b.key] = { count, avgPD, avgScore, trendIcon, trendText, trendColor, matching };
      });
    });

    return matrix;
  }, [applicants]);

  const handleCellClick = (type, riskBand) => {
    if (selectedHeatmapCell && selectedHeatmapCell.type === type && selectedHeatmapCell.riskBand === riskBand) {
      // Toggle off if clicking the same cell
      setSelectedHeatmapCell(null);
    } else {
      setSelectedHeatmapCell({ type, riskBand });
      if (type !== 'ALL') setActiveTab(type);
      setSelectedApplicant(null);
    }
  };

  // Filter based on NTC or MSME, heatmap cell selection, and search term
  const filtered = applicants.filter(a => {
    const isNTC = a.applicant_id?.toLowerCase().startsWith('ntc');
    const isMSME = a.applicant_id?.toLowerCase().startsWith('msme');
    
    // First apply tab filter
    if (activeTab === 'NTC' && !isNTC) return false;
    if (activeTab === 'MSME' && !isMSME) return false;

    // Heatmap cell filter
    if (selectedHeatmapCell) {
      const band = getRiskBand(a.default_probability ?? 0);
      if (selectedHeatmapCell.riskBand && band !== selectedHeatmapCell.riskBand) return false;
      if (selectedHeatmapCell.type && selectedHeatmapCell.type !== 'ALL') {
        if (selectedHeatmapCell.type === 'NTC' && !isNTC) return false;
        if (selectedHeatmapCell.type === 'MSME' && !isMSME) return false;
      }
    }

    // Then apply search filter
    return a.name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
           a.applicant_id?.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-body">
      {/* Header */}
      <div className="p-6 border-b border-white/10 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-white/5 rounded-full transition-colors hidden md:block">
              <ArrowLeft size={24} />
            </button>
            <div>
              <h1 className="text-3xl font-headline font-bold flex items-center gap-3">
                Loan Application Queue
                <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-3 py-1 rounded-full font-sans uppercase font-bold tracking-wider">
                  FintrixAi Officer
                </span>
              </h1>
              <p className="text-slate-400 text-sm mt-0.5">Review, compare, and decision applications with AI explainability</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 border border-white/10 rounded-lg bg-slate-950 p-1">
            <button 
              onClick={() => {setActiveTab('NTC'); setSelectedApplicant(null);}}
              className={`px-6 py-2 rounded-md font-semibold text-sm transition-all ${activeTab === 'NTC' ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              NTC Borrowers
            </button>
            <button 
              onClick={() => {setActiveTab('MSME'); setSelectedApplicant(null);}}
              className={`px-6 py-2 rounded-md font-semibold text-sm transition-all ${activeTab === 'MSME' ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              MSME Borrowers
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 max-w-7xl mx-auto w-full p-6 flex flex-col gap-6">

        {/* ── Feature B: Manager Portfolio Risk Heatmap ── */}
        <div className="bg-slate-900/80 border border-white/10 rounded-2xl p-6 backdrop-blur-xl shadow-2xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
                <Layers size={20} />
              </div>
              <div>
                <h2 className="text-xl font-headline font-bold text-white">Manager Portfolio Risk Heatmap</h2>
                <p className="text-xs text-slate-400">Aggregate risk distribution across MSME and NTC borrower segments. Click any cell to filter queue.</p>
              </div>
            </div>

            {selectedHeatmapCell && (
              <button
                onClick={() => setSelectedHeatmapCell(null)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-xs font-bold hover:bg-indigo-500/30 transition-all"
              >
                <Filter size={14} /> Clear Heatmap Filter
              </button>
            )}
          </div>

          {/* Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {RISK_BANDS.map((band) => {
              const ntcCell = heatmapMatrix['NTC']?.[band.key] || { count: 0, avgScore: null, trendIcon: null, trendText: '—' };
              const msmeCell = heatmapMatrix['MSME']?.[band.key] || { count: 0, avgScore: null, trendIcon: null, trendText: '—' };
              const isNtcActive = selectedHeatmapCell?.type === 'NTC' && selectedHeatmapCell?.riskBand === band.key;
              const isMsmeActive = selectedHeatmapCell?.type === 'MSME' && selectedHeatmapCell?.riskBand === band.key;

              return (
                <div key={band.key} className="flex flex-col gap-2">
                  <div className="flex justify-between items-center px-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">{band.label}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{band.pdRange}</span>
                  </div>

                  {/* NTC Cell Card */}
                  <div
                    onClick={() => handleCellClick('NTC', band.key)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${band.color} ${isNtcActive ? band.activeGlow : 'hover:scale-[1.02] opacity-90 hover:opacity-100'}`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-[10px] font-extrabold uppercase tracking-widest text-violet-300 bg-violet-950/60 px-2 py-0.5 rounded border border-violet-800/40">NTC</span>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white/10 font-mono">
                        {ntcCell.count} {ntcCell.count === 1 ? 'applicant' : 'applicants'}
                      </span>
                    </div>
                    <div className="flex justify-between items-end mt-2">
                      <div>
                        <div className="text-xs text-slate-400">Avg Score</div>
                        <div className="text-lg font-black font-mono text-white">{ntcCell.avgScore ? ntcCell.avgScore : '—'}</div>
                      </div>
                      <div className={`flex items-center gap-1 text-[11px] font-semibold ${ntcCell.trendColor}`}>
                        {ntcCell.trendIcon} {ntcCell.trendText}
                      </div>
                    </div>
                  </div>

                  {/* MSME Cell Card */}
                  <div
                    onClick={() => handleCellClick('MSME', band.key)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${band.color} ${isMsmeActive ? band.activeGlow : 'hover:scale-[1.02] opacity-90 hover:opacity-100'}`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-[10px] font-extrabold uppercase tracking-widest text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">MSME</span>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white/10 font-mono">
                        {msmeCell.count} {msmeCell.count === 1 ? 'applicant' : 'applicants'}
                      </span>
                    </div>
                    <div className="flex justify-between items-end mt-2">
                      <div>
                        <div className="text-xs text-slate-400">Avg Score</div>
                        <div className="text-lg font-black font-mono text-white">{msmeCell.avgScore ? msmeCell.avgScore : '—'}</div>
                      </div>
                      <div className={`flex items-center gap-1 text-[11px] font-semibold ${msmeCell.trendColor}`}>
                        {msmeCell.trendIcon} {msmeCell.trendText}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Filter Bar */}
          {selectedHeatmapCell && (
            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs">
              <span className="text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-violet-400 animate-ping"></span>
                Filtered by Heatmap Segment: <strong className="text-white font-headline">{selectedHeatmapCell.type}</strong> · <strong className="text-indigo-300 font-headline">{selectedHeatmapCell.riskBand.toUpperCase()} Risk</strong> ({filtered.length} matching)
              </span>
              <button onClick={() => setSelectedHeatmapCell(null)} className="text-indigo-400 hover:text-white font-bold underline">Clear Segment Filter</button>
            </div>
          )}
        </div>

        {/* Queue & Dossier Section */}
        <div className="flex-1 flex gap-6 w-full min-h-[500px]">
          {/* Left Side: Applicant List */}
          <div className={`w-full ${selectedApplicant ? 'lg:w-1/3 border-r border-white/10 pr-6' : 'w-full'} flex flex-col`}>
            <div className="p-4 border-b border-white/5 bg-slate-900/40 rounded-xl mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  type="text"
                  placeholder="Find applicant by ID or Name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-white/10 rounded-xl focus:ring-2 focus:ring-indigo-500 text-sm text-white placeholder-slate-500"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loading ? (
                <div className="flex justify-center py-20"><div className="w-8 h-8 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin"/></div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-slate-900/30 rounded-2xl border border-white/5">
                  <Users size={32} className="mx-auto mb-2 opacity-30" />
                  <p>No applicants found matching filter.</p>
                  {selectedHeatmapCell && (
                    <button onClick={() => setSelectedHeatmapCell(null)} className="mt-3 text-xs text-indigo-400 underline font-bold">Clear Heatmap Filter</button>
                  )}
                </div>
              ) : (
                filtered.map((app) => (
                  <motion.div
                    key={app.applicant_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => setSelectedApplicant(app)}
                    className={`p-4 rounded-xl cursor-pointer border transition-all ${selectedApplicant?.applicant_id === app.applicant_id ? 'bg-slate-800 border-indigo-500 shadow-lg shadow-indigo-500/20' : 'bg-slate-900 border-white/5 hover:border-white/20'}`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-bold text-lg text-white">{app.name}</h3>
                        <p className="text-xs font-mono text-slate-400">{app.applicant_id}</p>
                      </div>
                      <span className={`px-2.5 py-1 rounded text-xs font-bold font-mono ${app.default_probability < 0.2 ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-500/20' : app.default_probability < 0.5 ? 'text-amber-400 bg-amber-400/10 border border-amber-500/20' : 'text-rose-400 bg-rose-400/10 border border-rose-500/20'}`}>
                        {(app.default_probability * 100).toFixed(1)}% PD
                      </span>
                    </div>
                    <div className="flex justify-between items-center mt-3">
                      <span className="text-sm text-slate-400">Grade: <strong className="text-white font-mono">{app.grade}</strong></span>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                        app.decision === 'APPROVED' ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10' :
                        app.decision === 'REJECTED' ? 'border-rose-500/40 text-rose-400 bg-rose-500/10' :
                        'border-amber-500/40 text-amber-400 bg-amber-500/10'
                      }`}>
                        {app.decision}
                      </span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>

          {/* Right Side: Detailed Review Panel */}
          {selectedApplicant && (
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex-1 overflow-y-auto bg-slate-900/40 border border-white/10 rounded-2xl p-8 backdrop-blur-xl"
            >
              <div className="flex justify-between items-start mb-8">
                <div>
                  <span className="inline-block px-3 py-1 bg-white/5 text-slate-300 text-xs font-bold uppercase tracking-widest rounded-full mb-3">
                    Applicant Dossier
                  </span>
                  <h2 className="text-4xl font-headline font-extrabold text-white mb-2">{selectedApplicant.name}</h2>
                  <div className="flex items-center gap-4 text-slate-400 text-sm">
                    <span className="font-mono">{selectedApplicant.applicant_id}</span>
                    <span>•</span>
                    <span>{selectedApplicant.city || 'Location Unknown'}</span>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-sm text-slate-400 mb-1">Model Recommended Status</p>
                  <div className={`px-4 py-2 rounded-lg font-bold inline-block border ${
                        selectedApplicant.decision === 'APPROVED' ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400' :
                        selectedApplicant.decision === 'REJECTED' ? 'border-rose-500 bg-rose-500/10 text-rose-400' :
                        'border-amber-500 bg-amber-500/10 text-amber-500'
                      }`}>
                    {selectedApplicant.decision}
                  </div>
                </div>
              </div>

              {/* Application Data Grid */}
              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="p-6 bg-slate-950/80 rounded-2xl border border-white/5 shadow-inner">
                  <p className="text-sm text-slate-400 mb-2 flex items-center gap-2"><FileText size={16}/> Credit Grade</p>
                  <p className="text-5xl font-black font-mono text-white">{selectedApplicant.grade}</p>
                </div>
                <div className="p-6 bg-slate-950/80 rounded-2xl border border-white/5 shadow-inner">
                  <p className="text-sm text-slate-400 mb-2 flex items-center gap-2"><CheckCircle size={16}/> Prob. of Default</p>
                  <p className={`text-4xl font-black font-mono ${selectedApplicant.default_probability < 0.2 ? 'text-emerald-400' : selectedApplicant.default_probability < 0.5 ? 'text-amber-400' : 'text-rose-400'}`}>
                    {(selectedApplicant.default_probability * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="col-span-2 p-6 bg-slate-950/80 rounded-2xl border border-white/5 shadow-inner">
                  <p className="text-sm text-slate-400 mb-2 flex items-center gap-2"><MessageSquare size={16}/> AI Explainability Reason</p>
                  <p className="text-lg font-medium leading-relaxed italic text-indigo-200">
                    {selectedApplicant.primary_reason || "No specific model reason provided."}
                  </p>
                </div>
              </div>

              {/* Officer Action Area */}
              <div className="mt-8 bg-slate-950/90 border border-white/10 p-8 rounded-3xl shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 blur-[80px] rounded-full"></div>
                
                <h3 className="text-xl font-bold mb-4 font-headline text-white">Manager Review & Decision</h3>
                
                <label className="block text-sm font-medium text-slate-400 mb-2">Officer Remarks (Visible to Applicant)</label>
                <textarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-4 text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none min-h-[120px] mb-6 resize-none relative z-10 text-sm"
                  placeholder="Enter reasoning for your final decision here..."
                />

                <div className="flex gap-4 relative z-10">
                  <button 
                    onClick={() => handleAction('approve')}
                    className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.2)] transition-all flex justify-center items-center gap-2 text-lg active:scale-95"
                  >
                    <CheckCircle size={22} /> Approve Loan
                  </button>
                  <button 
                    onClick={() => handleAction('reject')}
                    className="flex-1 py-4 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl shadow-[0_0_20px_rgba(244,63,94,0.2)] transition-all flex justify-center items-center gap-2 text-lg active:scale-95"
                  >
                    <XCircle size={22} /> Decline Loan
                  </button>
                </div>
              </div>
            </motion.div>
          )}
          
          {!selectedApplicant && (
            <div className="hidden lg:flex flex-1 items-center justify-center flex-col text-slate-500 p-8 text-center bg-slate-900/20 border border-white/5 rounded-2xl">
              <Users size={64} className="mb-6 opacity-20 text-indigo-400" />
              <h3 className="text-2xl font-bold text-slate-300 mb-2">Select an Applicant</h3>
              <p className="max-w-md text-sm text-slate-400">Click on an applicant from the {activeTab} queue on the left to review their detailed risk dossier and submit a final decision.</p>
            </div>
          )}
        </div>
      </div>

      {/* Success Modal */}
      <AnimatePresence>
        {showStatusModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md"
          >
            <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }} className="bg-slate-900 p-8 rounded-3xl flex flex-col items-center border border-white/10 shadow-2xl">
              <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mb-4 border border-emerald-500/40">
                <CheckCircle size={32} />
              </div>
              <h2 className="text-2xl font-bold text-white">Decision Recorded!</h2>
              <p className="text-slate-400 mt-2 text-sm">The applicant status has been updated securely.</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
