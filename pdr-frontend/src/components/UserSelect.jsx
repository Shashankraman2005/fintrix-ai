import React, { useState } from 'react';
import './UserSelect.css';
import ThemeToggle from './ThemeToggle';

function UserSelect({ onScore, onBack, hasFetched, onFetched, loading, loadingText: propLoadingText }) {
  const [fetchMode, setFetchMode] = useState(hasFetched ? 'grid' : 'initial'); // 'initial' | 'loading' | 'grid'
  const [progress, setProgress] = useState(0);
  const [loadingText, setLoadingText] = useState('Connecting to Data Sources...');

  const startLoading = () => {
    setFetchMode('loading');
    const stages = [
      { text: "Connecting to Data Sources...", progress: 25, dot: 1 },
      { text: "Parsing Bank Statements (OCR)...", progress: 50, dot: 2 },
      { text: "Running Trust Intelligence Forensics...", progress: 75, dot: 3 },
      { text: "Preparing Scoring Interface...", progress: 100, dot: 4 }
    ];

    let startTime = null;
    const duration = 4000;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progressRaw = Math.min(elapsed / duration, 1);
      
      setProgress(Math.round(progressRaw * 100));

      const stageIndex = Math.floor(progressRaw * stages.length);
      const currentStage = stages[Math.min(stageIndex, stages.length - 1)];
      setLoadingText(currentStage.text);

      if (progressRaw < 1) {
        requestAnimationFrame(animate);
      } else {
        setTimeout(() => {
          setFetchMode('grid');
          if (onFetched) onFetched();
        }, 500);
      }
    };

    requestAnimationFrame(animate);
  };

  return (
    <div className="bg-surface dark:bg-slate-950 font-body text-on-surface dark:text-slate-200 min-h-screen">
      {/* Sidebar Navigation */}
      <aside className="h-screen w-72 fixed left-0 top-0 flex flex-col bg-slate-100 dark:bg-slate-900 z-40">
        <div className="flex flex-col h-full py-8 space-y-2">
          <div className="px-8 mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
              </div>
              <div>
                <h1 className="font-headline font-bold text-slate-900 dark:text-white leading-tight">FintrixAi</h1>
                <p className="font-inter text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400">v4.2.0 Active</p>
              </div>
            </div>
          </div>
          <nav className="flex-1 px-4 space-y-1">
            <a className="flex items-center gap-4 bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm rounded-r-full mr-4 px-6 py-3 font-bold" href="#">
              <span className="material-symbols-outlined cursor-default">person</span>
              <span className="font-inter text-sm">Users</span>
            </a>
          </nav>
          <div className="px-8 mt-auto pt-8 border-t border-slate-200/10">
            <div className="space-y-1">
              <a className="flex items-center gap-4 text-slate-500 dark:text-slate-400 px-6 py-2 hover:text-slate-900 dark:text-white dark:hover:text-white" href="#">
                <span className="material-symbols-outlined text-lg">help</span>
                <span className="font-inter text-xs uppercase tracking-widest">Support</span>
              </a>
              <a className="flex items-center gap-4 text-slate-500 dark:text-slate-400 px-6 py-2 hover:text-slate-900 dark:text-white dark:hover:text-white" href="#">
                <span className="material-symbols-outlined text-lg">logout</span>
                <span className="font-inter text-xs uppercase tracking-widest">Sign Out</span>
              </a>
            </div>
          </div>
        </div>
      </aside>

      {/* Top App Bar */}
      <header className="fixed top-0 right-0 left-72 z-30 bg-slate-50/80 dark:bg-slate-950/80 backdrop-blur-xl shadow-sm shadow-slate-200/20 dark:shadow-none px-8 py-3 flex justify-between items-center">
        <div className="flex items-center gap-8"></div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <button className="p-2 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 rounded-full transition-all active:scale-95">
            <span className="material-symbols-outlined text-slate-600 dark:text-slate-300">settings</span>
          </button>
          <div className="w-8 h-8 rounded-full overflow-hidden bg-slate-200 ml-2">
            <img alt="User Profile Avatar" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDxY3s6-7FBK7X7Vtc-7HTIWBm84R9ve7hhOVRqWTHFzhs9bKQvQ94Ek2RvQrqTUoIoaofW6p7ldVxnTj9cNacjUnATuRhgTq0LQmUA9MeWe7Wc6GmUPwYigAlyTRloKQ3eF47RHECgp2QBLzdskh9Sl4usYgKu82EslbowvK5yjTY7_vEzRAoKnFbQYstBTabEU8zPKfRvFb70idW4Ft_1RODcEfKbxRiW9oYGasC0F7LtFoQo7IVxFAq9OSdYVCssgtDdhu9e-Q" />
          </div>
        </div>
      </header>

      <main className="ml-72 pt-24 px-12 pb-20">
        <section className="mb-16">
          <div className="mb-12">
            <button onClick={onBack} className="text-secondary dark:text-slate-400 text-sm flex items-center gap-1 hover:text-primary dark:text-white dark:hover:text-white transition-colors mb-6 group bg-transparent border-none cursor-pointer">
              <span className="material-symbols-outlined text-sm transition-transform group-hover:-translate-x-1">arrow_back</span> Back
            </button>
            <h2 className="text-4xl font-headline font-extrabold text-slate-900 dark:text-white mb-2 tracking-tight">Alternative Credit Intelligence</h2>
            <p className="text-on-surface-variant dark:text-slate-400 text-lg">Select a sandbox profile to run through the multi-layer risk evaluation pipeline.</p>
          </div>

          {/* Initial State */}
          {fetchMode === 'initial' && (
            <div className="flex flex-col items-center justify-center py-24 bg-white/50 dark:bg-slate-900/50 border border-dashed border-slate-300 dark:border-slate-700 rounded-3xl animate-reveal">
              <div className="w-16 h-16 bg-primary-container dark:bg-slate-800 text-primary dark:text-slate-200 rounded-2xl flex items-center justify-center mb-6">
                <span className="material-symbols-outlined text-3xl">database</span>
              </div>
              <h3 className="text-2xl font-headline font-bold text-slate-900 dark:text-white mb-2">Initialize Sandbox Environment</h3>
              <p className="text-secondary dark:text-slate-400 mb-8 text-center max-w-md">Fetch real-time financial snapshots from our sandboxed data sources to begin analysis.</p>
              <button 
                onClick={startLoading}
                className="bg-slate-900 dark:bg-white dark:text-slate-900 dark:text-white text-white px-8 py-4 rounded-full font-bold shadow-xl hover:bg-slate-800 dark:hover:bg-slate-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3">
                <span className="material-symbols-outlined">sync</span>
                Fetch Demo Profiles
              </button>
            </div>
          )}

          {/* Loading State */}
          {fetchMode === 'loading' && (
            <div className="py-32 flex flex-col items-center justify-center">
              <div className="w-full max-w-md">
                <div className="flex justify-between items-end mb-4">
                  <div className="pulse-container">
                    <span className="text-primary dark:text-slate-200 font-bold text-lg">{loadingText}</span>
                  </div>
                  <span className="text-slate-400 font-mono text-sm">{progress}%</span>
                </div>
                <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div className="progress-bar-fill h-full bg-primary" style={{ width: `${progress}%` }}></div>
                </div>
                <div className="mt-8 flex justify-center gap-12">
                  {[
                    { dot: 1, label: 'Connect', active: progress > 0 },
                    { dot: 2, label: 'Parse', active: progress >= 25 },
                    { dot: 3, label: 'Forensics', active: progress >= 50 },
                    { dot: 4, label: 'Score', active: progress >= 75 }
                  ].map(s => (
                    <div key={s.dot} className="flex flex-col items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${s.active ? 'bg-primary' : 'bg-primary/20 dark:bg-slate-700'}`}></div>
                      <span className="text-[10px] uppercase tracking-tighter text-slate-400 font-bold">{s.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Grid State */}
          {fetchMode === 'grid' && (
             <div className="animate-reveal">
               {/* NTC Section */}
               <div className="mb-16">
                 <div className="flex items-center gap-4 mb-8">
                   <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-on-surface-variant dark:text-slate-400">NTC (New-to-Credit)</h3>
                   <div className="flex-1 h-px bg-slate-200 dark:bg-slate-800"></div>
                 </div>
                 <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                   
                   {/* User 1 */}
                   <div className="bg-surface-container-lowest dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-xl shadow-slate-400 dark:shadow-none hover:shadow-2xl hover:shadow-slate-500 dark:hover:bg-slate-800/50 hover:-translate-y-1 transition-all flex flex-col group">
                     <div className="flex justify-between items-start mb-8">
                       <span className="text-[10px] font-bold text-on-surface-variant dark:text-slate-400 tracking-widest uppercase">NTC Profile</span>
                     </div>
                     <h4 className="text-xl font-headline font-bold text-on-surface dark:text-white mb-1">Priya Venkataraman</h4>
                     <p className="text-xs text-on-surface-variant dark:text-slate-400 mb-2">Chennai, Tamil Nadu</p>
                     <p className="text-sm text-secondary dark:text-slate-300 font-medium mb-12">Clean Salaried Professional with consistent digital footprint.</p>
                     <div className="mt-auto">
                       <div className="flex flex-wrap gap-2 mb-6">
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Individual</span>
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Salaried</span>
                       </div>
                       <button onClick={() => onScore('NTC_001')} className="w-full gradient-cta text-white rounded-full py-3 text-center font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] shadow-lg shadow-emerald-900/20 dark:shadow-none transition-all cursor-pointer">
                         Fetch & score <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                       </button>
                     </div>
                   </div>

                   {/* User 2 */}
                   <div className="bg-surface-container-lowest dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-xl shadow-slate-400 dark:shadow-none hover:shadow-2xl hover:shadow-slate-500 dark:hover:bg-slate-800/50 hover:-translate-y-1 transition-all flex flex-col group">
                     <div className="flex justify-between items-start mb-8">
                       <span className="text-[10px] font-bold text-on-surface-variant dark:text-slate-400 tracking-widest uppercase">NTC Profile</span>
                     </div>
                     <h4 className="text-xl font-headline font-bold text-on-surface dark:text-white mb-1">Ramesh Gowda</h4>
                     <p className="text-xs text-on-surface-variant dark:text-slate-400 mb-2">Mysuru, Karnataka</p>
                     <p className="text-sm text-secondary dark:text-slate-300 font-medium mb-12">Cash-Dependent Informal Worker with sporadic banking.</p>
                     <div className="mt-auto">
                       <div className="flex flex-wrap gap-2 mb-6">
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Individual</span>
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Informal</span>
                       </div>
                       <button onClick={() => onScore('NTC_002')} className="w-full gradient-cta text-white rounded-full py-3 text-center font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] shadow-lg shadow-emerald-900/20 dark:shadow-none transition-all cursor-pointer">
                         Fetch & score <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                       </button>
                     </div>
                   </div>

                   {/* User 3 */}
                   <div className="bg-surface-container-lowest dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-xl shadow-slate-400 dark:shadow-none hover:shadow-2xl hover:shadow-slate-500 dark:hover:bg-slate-800/50 hover:-translate-y-1 transition-all flex flex-col group">
                     <div className="flex justify-between items-start mb-8">
                       <span className="text-[10px] font-bold text-on-surface-variant dark:text-slate-400 tracking-widest uppercase">NTC Profile</span>
                     </div>
                     <h4 className="text-xl font-headline font-bold text-on-surface dark:text-white mb-1">Deepak Malhotra</h4>
                     <p className="text-xs text-on-surface-variant dark:text-slate-400 mb-2">Delhi, NCR</p>
                     <p className="text-sm text-secondary dark:text-slate-300 font-medium mb-12">Synthetic Fraud — Artificially inflated balance history.</p>
                     <div className="mt-auto">
                       <div className="flex flex-wrap gap-2 mb-6">
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Individual</span>
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Fraud Risk</span>
                       </div>
                       <button onClick={() => onScore('NTC_003')} className="w-full gradient-cta text-white rounded-full py-3 text-center font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] shadow-lg shadow-emerald-900/20 dark:shadow-none transition-all cursor-pointer">
                         Fetch & score <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                       </button>
                     </div>
                   </div>
                 </div>
               </div>

               {/* MSME Section */}
               <div className="mb-16">
                 <div className="flex items-center gap-4 mb-8">
                   <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-on-surface-variant dark:text-slate-400">MSME (Micro, Small & Medium Enterprises)</h3>
                   <div className="flex-1 h-px bg-slate-200 dark:bg-slate-800"></div>
                 </div>
                 <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                   
                   {/* User 4 */}
                   <div className="bg-surface-container-lowest dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-xl shadow-slate-400 dark:shadow-none hover:shadow-2xl hover:shadow-slate-500 dark:hover:bg-slate-800/50 hover:-translate-y-1 transition-all flex flex-col group">
                     <div className="flex justify-between items-start mb-8">
                       <span className="text-[10px] font-bold text-on-surface-variant dark:text-slate-400 tracking-widest uppercase">MSME Entity</span>
                     </div>
                     <h4 className="text-xl font-headline font-bold text-on-surface dark:text-white mb-1">Sukhwinder Singh</h4>
                     <p className="text-xs text-on-surface-variant dark:text-slate-400 mb-2">Ludhiana, Punjab</p>
                     <p className="text-sm text-secondary dark:text-slate-300 font-medium mb-12">Seasonal Agri Business with verifiable mandi receipts.</p>
                     <div className="mt-auto">
                       <div className="flex flex-wrap gap-2 mb-6">
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Agriculture</span>
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Seasonal</span>
                       </div>
                       <button onClick={() => onScore('MSME_001')} className="w-full gradient-cta text-white rounded-full py-3 text-center font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] shadow-lg shadow-emerald-900/20 dark:shadow-none transition-all cursor-pointer">
                         Fetch & score <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                       </button>
                     </div>
                   </div>

                   {/* User 5 */}
                   <div className="bg-surface-container-lowest dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-xl shadow-slate-400 dark:shadow-none hover:shadow-2xl hover:shadow-slate-500 dark:hover:bg-slate-800/50 hover:-translate-y-1 transition-all flex flex-col group">
                     <div className="flex justify-between items-start mb-8">
                       <span className="text-[10px] font-bold text-on-surface-variant dark:text-slate-400 tracking-widest uppercase">MSME Entity</span>
                     </div>
                     <h4 className="text-xl font-headline font-bold text-on-surface dark:text-white mb-1">Mohammed Farouk</h4>
                     <p className="text-xs text-on-surface-variant dark:text-slate-400 mb-2">Delhi, NCR</p>
                     <p className="text-sm text-secondary dark:text-slate-300 font-medium mb-12">Circular Transaction Fraud patterns detected in ledger.</p>
                     <div className="mt-auto">
                       <div className="flex flex-wrap gap-2 mb-6">
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Trading</span>
                         <span className="bg-surface-container dark:bg-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-on-surface-variant dark:text-slate-300">Circular Risk</span>
                       </div>
                       <button onClick={() => onScore('MSME_002')} className="w-full gradient-cta text-white rounded-full py-3 text-center font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] shadow-lg shadow-emerald-900/20 dark:shadow-none transition-all cursor-pointer">
                         Fetch & score <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                       </button>
                     </div>
                   </div>
                 </div>
               </div>
             </div>
          )}

        </section>
      </main>

      {/* Analysis Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex flex-col items-center justify-center animate-reveal">
          <div className="bg-white dark:bg-slate-900 p-10 rounded-3xl shadow-2xl flex flex-col items-center max-w-sm w-full text-center border border-slate-200 dark:border-slate-800">
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 text-primary dark:text-slate-200 rounded-full flex items-center justify-center mb-6">
               <span className="material-symbols-outlined text-3xl animate-spin">autorenew</span>
            </div>
            <h3 className="text-xl font-headline font-bold text-slate-900 dark:text-white mb-2">Analyzing Profile</h3>
            <p className="text-secondary dark:text-slate-400 font-medium text-sm animate-pulse">{propLoadingText || 'Processing parameters...'}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserSelect;
