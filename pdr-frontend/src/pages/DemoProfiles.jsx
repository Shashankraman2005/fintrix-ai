import React, { useState, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import demoData from '../../../demo_users.json';
import ThemeToggle from '../components/ThemeToggle';
import StarField from '../components/StarField';
import NavUser from '../components/NavUser';

const gradeColors = {
  A: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  B: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  C: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  D: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
  E: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
};

const typeBadge = {
  NTC: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', label: 'NTC' },
  MSME: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', label: 'MSME' },
  MSME_MIDDLEMAN: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', label: 'MSME' },
};

const AA_STEPS = [
  { text: 'Establishing secure connection to AA gateway...', duration: 600 },
  { text: 'Verifying loan officer consent token...', duration: 500 },
  { text: 'Requesting FIP data from linked bank accounts...', duration: 700 },
  { text: 'Decrypting financial information packets...', duration: 500 },
  { text: 'Parsing 6-month transaction histories...', duration: 400 },
  { text: 'Mapping to FintrixAi credit assessment schema...', duration: 300 },
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function DemoProfiles() {
  const navigate = useNavigate();
  const users = demoData.demo_users;

  const [phase, setPhase] = useState('initial');
  const [visibleCount, setVisibleCount] = useState(0);
  const [doneCount, setDoneCount] = useState(0);
  const [readyVisible, setReadyVisible] = useState(false);
  const [cardsVisible, setCardsVisible] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const fetchingRef = useRef(false);

  const progressPct = AA_STEPS.length > 0
    ? Math.round((doneCount / AA_STEPS.length) * 100)
    : 0;

  const handleFetch = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setPhase('fetching');

    for (let i = 0; i < AA_STEPS.length; i++) {
      setVisibleCount(i + 1);
      await sleep(AA_STEPS[i].duration);
      setDoneCount(i + 1);
    }

    setReadyVisible(true);
    await sleep(500);
    setPhase('select_type');
  }, []);

  const handleTypeSelect = (type) => {
    setSelectedType(type);
    setCardsVisible(false);
    setPhase('loaded');
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setCardsVisible(true);
      });
    });
  };

  const handleSelect = (user) => {
    localStorage.setItem('fintrixai_demo_user', JSON.stringify({
      user_id: user.user_id,
      name: user.user_profile?.name || user.form_fields?.full_name || user.form_fields?.applicant_name,
      model: user.model.startsWith('MSME') ? 'MSME' : 'NTC',
      form_fields: user.form_fields,
    }));
    localStorage.setItem('pdr_demo_user', JSON.stringify({
      user_id: user.user_id,
      name: user.user_profile?.name || user.form_fields?.full_name || user.form_fields?.applicant_name,
      model: user.model.startsWith('MSME') ? 'MSME' : 'NTC',
      form_fields: user.form_fields,
    }));
    navigate('/solutions');
  };

  return (
    <div className="bg-surface dark:bg-slate-950 text-on-surface dark:text-slate-200 min-h-screen font-body antialiased">
      <StarField />
      {/* Nav */}
      <nav className="bg-[#f7f9fb]/80 dark:bg-slate-950/80 backdrop-blur-xl top-0 sticky z-50 shadow-sm shadow-slate-200/50 dark:shadow-none font-['Manrope'] antialiased tracking-tight">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link to="/" className="text-xl font-bold tracking-tighter text-slate-900 dark:text-slate-50">FintrixAi</Link>
          <div className="hidden md:flex items-center gap-x-8">
            <Link to="/" className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300">Home</Link>
            <Link to="/solutions" className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300">Solutions</Link>
            <span className="text-slate-900 dark:text-white font-semibold border-b-2 border-slate-900 dark:border-white pb-1">Demo Profiles</span>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <NavUser />
            <Link to="/solutions" className="gradient-cta text-white px-6 py-2.5 rounded-lg font-semibold active:scale-95 transition-transform duration-200">Score a Business</Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 pt-16 pb-24">

        <AnimatePresence mode="wait">
        {/* ── STATE 1: INITIAL ── */}
        {phase === 'initial' && (
          <motion.div 
            key="initial"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center justify-center min-h-[60vh] text-center"
          >
            {/* ... rest unchanged but wrapped ... */}
            <div className="w-16 h-16 rounded-2xl bg-[#0F172A] flex items-center justify-center mb-8 shadow-lg">
              <span className="material-symbols-outlined text-white text-3xl">verified_user</span>
            </div>

            <h1 className="text-4xl md:text-5xl font-headline font-extrabold text-slate-900 dark:text-slate-50 tracking-tighter mb-4">
              Fetch users
            </h1>
            <p className="text-lg text-on-surface-variant dark:text-slate-400 max-w-xl mx-auto leading-relaxed mb-10">
              Pull financial profiles from server
            </p>

            <button
              onClick={handleFetch}
              className="gradient-cta text-white px-10 py-4 rounded-lg text-lg font-bold flex items-center gap-3 shadow-lg shadow-tertiary/20 active:scale-95 transition-transform duration-200"
            >
              <span className="material-symbols-outlined text-xl">sync_lock</span>
              Initiate Data Pull
            </button>

            <p className="mt-8 text-[13px] text-slate-800 tracking-wide">
              Simulated AA flow for demonstration purposes
            </p>
          </motion.div>
        )}

        {/* ── STATE 2: FETCHING ── */}
        {phase === 'fetching' && (
          <motion.div 
            key="fetching"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="flex flex-col items-center justify-center min-h-[60vh]"
          >
            <div className="w-full max-w-lg bg-white dark:bg-[#0F172A] rounded-2xl shadow-xl dark:shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              {/* Progress bar */}
              <div className="h-1 w-full bg-slate-100 dark:bg-slate-800">
                <div
                  className="h-full bg-emerald-500 dark:bg-emerald-400 transition-all duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                ></div>
              </div>

              {/* Title bar */}
              <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-transparent">
                <span className="material-symbols-outlined text-emerald-600 dark:text-emerald-400 text-base">verified_user</span>
                <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 tracking-wide">aa-gateway · secure-session</span>
              </div>

              {/* Step log */}
              <div className="px-6 py-6 font-mono text-sm space-y-3 min-h-[280px]">
                {AA_STEPS.slice(0, visibleCount).map((step, i) => {
                  const isDone = i < doneCount;
                  return (
                    <div
                      key={i}
                      className="flex items-start gap-3 animate-[fadeIn_0.25s_ease-out]"
                    >
                      {isDone ? (
                        <span className="material-symbols-outlined text-emerald-600 dark:text-emerald-400 text-base mt-0.5 shrink-0">check_circle</span>
                      ) : (
                        <span className="material-symbols-outlined text-slate-400 dark:text-slate-500 text-base mt-0.5 shrink-0 animate-spin">progress_activity</span>
                      )}
                      <span className={isDone ? 'text-slate-400 dark:text-slate-500' : 'text-slate-900 dark:text-slate-200 font-medium'}>
                        {step.text}
                      </span>
                    </div>
                  );
                })}
                {readyVisible && (
                  <div className="flex items-start gap-3 pt-2 animate-[fadeIn_0.25s_ease-out]">
                    <span className="material-symbols-outlined text-emerald-600 dark:text-emerald-400 text-base mt-0.5 shrink-0">rocket_launch</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">Profiles ready for assessment.</span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* ── STATE 3: SELECT TYPE ── */}
        {phase === 'select_type' && (
          <motion.div 
            key="select_type"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="flex flex-col items-center justify-center min-h-[60vh] text-center"
          >
            <div className="inline-block px-4 py-1.5 mb-6 rounded-full bg-tertiary-container text-on-tertiary-container text-xs font-bold tracking-widest uppercase font-label">
              AA Gateway · Profiles Ready
            </div>
            <h1 className="text-4xl md:text-5xl font-headline font-extrabold text-slate-900 dark:text-slate-50 tracking-tighter mb-4">
              Select Applicant Type
            </h1>
            <p className="text-lg text-on-surface-variant dark:text-slate-400 max-w-xl mx-auto leading-relaxed mb-12">
              Choose the category you want to assess. FintrixAi runs a dedicated scoring pipeline for each type.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl text-left">
              {/* NTC Card */}
              <button
                onClick={() => handleTypeSelect('NTC')}
                className="group bg-surface-container-lowest dark:bg-slate-900 border-2 border-outline-variant/20 dark:border-slate-800 hover:border-violet-400 dark:hover:border-violet-500 rounded-2xl p-8 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-500/10 active:scale-[0.98]"
              >
                <div className="w-12 h-12 rounded-xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center mb-5">
                  <span className="material-symbols-outlined text-violet-600 dark:text-violet-400 text-2xl">person</span>
                </div>
                <div className="inline-flex items-center px-3 py-1 rounded-full bg-violet-50 dark:bg-violet-900/30 border border-violet-200 dark:border-violet-700 mb-4">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-violet-700 dark:text-violet-300">NTC</span>
                </div>
                <h2 className="text-xl font-headline font-bold text-slate-900 dark:text-slate-50 mb-2">New-to-Credit Individuals</h2>
                <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed mb-6">
                  Salaried professionals, informal workers, and gig workers without a formal credit bureau history. Scored using behavioral and alternative data signals.
                </p>
                <div className="flex items-center gap-2 text-violet-600 dark:text-violet-400 font-bold text-sm">
                  <span>View {users.filter(u => u.model === 'NTC').length} NTC profiles</span>
                  <span className="material-symbols-outlined text-base group-hover:translate-x-1 transition-transform">arrow_forward</span>
                </div>
              </button>

              {/* MSME Card */}
              <button
                onClick={() => handleTypeSelect('MSME')}
                className="group bg-surface-container-lowest dark:bg-slate-900 border-2 border-outline-variant/20 dark:border-slate-800 hover:border-sky-400 dark:hover:border-sky-500 rounded-2xl p-8 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-sky-500/10 active:scale-[0.98]"
              >
                <div className="w-12 h-12 rounded-xl bg-sky-50 dark:bg-sky-900/30 flex items-center justify-center mb-5">
                  <span className="material-symbols-outlined text-sky-600 dark:text-sky-400 text-2xl">storefront</span>
                </div>
                <div className="inline-flex items-center px-3 py-1 rounded-full bg-sky-50 dark:bg-sky-900/30 border border-sky-200 dark:border-sky-700 mb-4">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-sky-700 dark:text-violet-300">MSME</span>
                </div>
                <h2 className="text-xl font-headline font-bold text-slate-900 dark:text-slate-50 mb-2">Micro & Small Enterprises</h2>
                <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed mb-6">
                  Kirana stores, seasonal agri businesses, traders, and manufacturers. Scored using GST compliance, cash flow patterns, and business health signals.
                </p>
                <div className="flex items-center gap-2 text-sky-600 dark:text-sky-400 font-bold text-sm">
                  <span>View 3 MSME profiles</span>
                  <span className="material-symbols-outlined text-base group-hover:translate-x-1 transition-transform">arrow_forward</span>
                </div>
              </button>
            </div>

            <div className="mt-12">
              <Link to="/" className="text-sm text-slate-400 hover:text-slate-600 dark:text-slate-300 transition-colors">
                &larr; Back to Home
              </Link>
            </div>
          </motion.div>
        )}

        {/* ── STATE 4: LOADED ── */}
        {phase === 'loaded' && (
          <motion.div 
            key="loaded"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* Header */}
            <div className={`text-center mb-10 transition-all duration-500 ${cardsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <div className="inline-block px-4 py-1.5 mb-6 rounded-full bg-tertiary-container text-on-tertiary-container text-xs font-bold tracking-widest uppercase font-label">
                AA Gateway · {selectedType === 'MSME' ? 'MSME Profiles' : 'NTC Profiles'}
              </div>
              <h1 className="text-4xl md:text-5xl font-headline font-extrabold text-slate-900 dark:text-slate-50 tracking-tighter mb-4">
                {selectedType === 'MSME' ? 'Micro & Small Enterprise Profiles' : 'New-to-Credit Individual Profiles'}
              </h1>
              <p className="text-lg text-on-surface-variant dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
                {selectedType === 'MSME'
                  ? 'See how FintrixAi scores small businesses — seasonal agri, trading entities, and fraud cases.'
                  : 'See how FintrixAi scores individuals — salaried professionals, informal workers, and fraud cases.'}
              </p>
            </div>

            {/* Back + instruction */}
            <div className={`flex items-center justify-between mb-8 transition-all duration-500 delay-100 ${cardsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <button
                onClick={() => setPhase('select_type')}
                className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors bg-transparent border-none cursor-pointer"
              >
                <span className="material-symbols-outlined text-base">arrow_back</span>
                Change type
              </button>
              <p className="text-xs text-slate-400">Select an applicant to begin credit assessment</p>
            </div>

            {/* Cards Grid */}
            <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 transition-all duration-700 delay-150 ${cardsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
              {users.filter(u => selectedType === 'MSME' ? u.model.startsWith('MSME') : u.model === 'NTC').map((user) => {
                // eslint-disable-next-line no-unused-vars
                const grade = gradeColors[user.expected_grade] || gradeColors.C;
                const type = typeBadge[user.model] || typeBadge.NTC;
                const displayName = user.user_profile?.name || 'Unknown';

                return (
                  <div
                    key={user.user_id}
                    className="group bg-surface-container-lowest dark:bg-slate-900 rounded-2xl border border-outline-variant/15 dark:border-slate-800 hover:border-tertiary/40 dark:hover:border-tertiary/40 transition-all duration-500 flex flex-col overflow-hidden"
                  >
                    <div className="p-8 flex flex-col flex-1">
                      {/* Badges row */}
                      <div className="flex items-center gap-2 mb-5">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border ${type.bg} ${type.text} ${type.border}`}>
                          {type.label}
                        </span>

                      </div>

                      {/* Name */}
                      <h3 className="text-xl font-headline font-bold text-slate-900 dark:text-slate-50 mb-1">{displayName}</h3>
                      <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant dark:text-slate-400/60 dark:text-slate-400 mb-4">{user.persona}</p>

                      {/* Story */}
                      <p className="text-sm text-on-surface-variant dark:text-slate-300 leading-relaxed flex-1">{user.story}</p>

                      {/* Data source line */}
                      <p className="mt-4 text-[11px] text-slate-400 flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-xs">verified_user</span>
                        Data source: AA Gateway &middot; 6-month history
                      </p>

                      {/* Select button */}
                      <button
                        onClick={() => handleSelect(user)}
                        className="mt-4 w-full py-3 rounded-lg text-sm font-bold tracking-wide gradient-cta text-white shadow-lg shadow-emerald-900/20 dark:shadow-none hover:opacity-90 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2"
                      >
                        Select Profile
                        <span className="material-symbols-outlined text-base">arrow_forward</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Bottom back to home */}
            <div className={`text-center mt-12 transition-all duration-500 delay-200 ${cardsVisible ? 'opacity-100' : 'opacity-0'}`}>
              <Link to="/" className="text-sm text-slate-400 hover:text-slate-600 dark:text-slate-300 transition-colors">
                &larr; Back to Home
              </Link>
            </div>
          </motion.div>
        )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default DemoProfiles;
