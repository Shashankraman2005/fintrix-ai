import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, User as UserIcon, Clock, CheckCircle, XCircle, ArrowLeft, MessageSquare, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import StarField from '../components/StarField';

import { BACKEND_URL } from '../config';

export default function UserStatus() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [applicantId, setApplicantId] = useState('');
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setAuthLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleGoogleLogin = async () => {
    try {
      setError('');
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.error(err);
      setError('Authentication failed. Please try again.');
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setStatusData(null);
      setApplicantId('');
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  const checkStatus = async (e) => {
    e.preventDefault();
    if (!applicantId.trim()) return;
    
    setLoading(true);
    setError('');
    setStatusData(null);

    try {
      const res = await axios.get(`${BACKEND_URL}/api/user/status/${applicantId}`);
      setStatusData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Applicant ID not found or server error.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (outcome) => {
    if (!outcome) return <Clock className="text-amber-400" size={48} />;
    const normalized = outcome.toLowerCase();
    if (normalized.includes('approve')) return <CheckCircle className="text-green-400" size={48} />;
    if (normalized.includes('reject')) return <XCircle className="text-rose-400" size={48} />;
    return <Clock className="text-amber-400" size={48} />;
  };

  const getStatusColor = (outcome) => {
    if (!outcome) return 'border-amber-500/30 bg-amber-500/5 text-amber-400';
    const normalized = outcome.toLowerCase();
    if (normalized.includes('approve')) return 'border-green-500/30 bg-green-500/5 text-green-400';
    if (normalized.includes('reject')) return 'border-rose-500/30 bg-rose-500/5 text-rose-400';
    return 'border-amber-500/30 bg-amber-500/5 text-amber-400';
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
         <Loader2 className="animate-spin text-primary" size={48} />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 overflow-hidden">
      <StarField />
      
      <button 
        onClick={() => navigate('/')} 
        className="absolute top-8 left-8 p-3 text-slate-400 hover:text-white hover:bg-white/10 rounded-full transition-all z-20 flex items-center gap-2"
      >
        <ArrowLeft /> Home
      </button>

      {user && (
        <button 
          onClick={handleLogout} 
          className="absolute top-8 right-8 p-3 text-slate-400 hover:text-white hover:bg-white/10 rounded-full transition-all z-20 flex items-center gap-2 text-sm font-medium"
        >
          <LogOut size={16} /> Sign Out
        </button>
      )}

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg z-10"
      >
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-primary/20 text-primary rounded-2xl flex items-center justify-center mx-auto mb-4 border border-primary/40 rotate-3">
            <UserIcon size={32} className="-rotate-3" />
          </div>
          <h1 className="text-4xl font-headline font-bold text-white mb-3">Application Tracker</h1>
          <p className="text-slate-400 text-lg">Check the real-time status of your loan application securely.</p>
        </div>

        {!user ? (
           <div className="bg-surface/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 text-center shadow-2xl">
              <h2 className="text-xl font-bold text-white mb-6">Verify Your Identity</h2>
              <button
                onClick={handleGoogleLogin}
                className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 text-slate-800 font-bold py-3 px-4 rounded-xl transition-all shadow-lg focus:ring-4 focus:ring-white/30"
              >
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" className="w-6 h-6" />
                Sign in with Google
              </button>
              {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
           </div>
        ) : (
          <>
            <form onSubmit={checkStatus} className="mb-8">
              <div className="relative flex shadow-2xl">
                <input
                  type="text"
                  value={applicantId}
                  onChange={(e) => setApplicantId(e.target.value)}
                  placeholder="Enter your Applicant ID (e.g. ntc_001)"
                  className="w-full bg-surface/80 backdrop-blur-xl border border-white/10 border-r-0 rounded-l-2xl py-4 pl-6 pr-4 text-white placeholder-slate-500 focus:outline-none focus:bg-slate-900 transition-colors"
                />
                <button 
                  type="submit"
                  disabled={loading}
                  className="bg-primary hover:bg-primary-hover text-white px-8 rounded-r-2xl font-bold transition-colors flex items-center justify-center min-w-[120px]"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <span>Track <Search className="inline ml-1" size={18}/></span>}
                </button>
              </div>
              {error && (
                <motion.p initial={{opacity:0}} animate={{opacity:1}} className="text-rose-400 mt-3 text-center bg-rose-500/10 py-2 rounded-lg border border-rose-500/20">
                  {error}
                </motion.p>
              )}
            </form>

            <AnimatePresence mode="wait">
              {statusData && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className={`p-8 rounded-3xl border backdrop-blur-xl shadow-[0_0_40px_rgba(0,0,0,0.5)] ${getStatusColor(statusData.outcome)}`}
                >
                  <div className="flex flex-col items-center text-center">
                    <div className="mb-4 drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                      {getStatusIcon(statusData.outcome)}
                    </div>
                    
                    <h2 className="text-sm font-semibold tracking-widest uppercase mb-1 opacity-80">Application Status</h2>
                    <p className="text-4xl font-black mb-6 tracking-tight text-white drop-shadow-md">
                      {statusData.outcome || 'PENDING / MANUAL REVIEW'}
                    </p>

                    <div className="w-full space-y-4 text-left bg-slate-950/50 p-6 rounded-2xl border border-white/5">
                      <div className="flex justify-between items-center border-b border-white/5 pb-3">
                        <span className="text-slate-400">Applicant Name</span>
                        <span className="font-medium text-white">{statusData.name || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between items-center border-b border-white/5 pb-3">
                        <span className="text-slate-400">FintrixAi Grade</span>
                        <span className="font-bold text-white text-lg">{statusData.grade}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Last Updated</span>
                        <span className="font-mono text-white text-sm">
                          {new Date(statusData.score_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {/* Manager Remarks showing to user */}
                    {statusData.manager_remarks && (
                      <div className="w-full mt-4 p-5 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl text-left">
                        <h4 className="text-indigo-300 font-semibold mb-2 flex items-center gap-2">
                          <MessageSquare size={16} /> Officer Note
                        </h4>
                        <p className="text-white italic leading-relaxed">{statusData.manager_remarks}</p>
                      </div>
                    )}
                    
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </motion.div>
    </div>
  );
}
