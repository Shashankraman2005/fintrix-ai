import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import ThemeToggle from '../components/ThemeToggle';
import StarField from '../components/StarField';
import NavUser from '../components/NavUser';

function LandingPage() {
  const [activeCard, setActiveCard] = useState(null);
  const toggleCard = (key) => setActiveCard(prev => prev === key ? null : key);

  // Returns animate target for a focused card — used on INNER motion.div only (no whileInView conflict)
  const focusAnimate = (key) => {
    const isActive = activeCard === key;
    const isDimmed = activeCard !== null && !isActive;
    return {
      scale: isActive ? 1.06 : 1,
      opacity: 1,
      boxShadow: isActive
        ? '0 0 0 2.5px rgba(130,255,153,1), 0 0 80px 24px rgba(130,255,153,0.35), 0 30px 80px rgba(0,0,0,0.4)'
        : '0 0 0 0px rgba(130,255,153,0), 0 0 0px 0px rgba(130,255,153,0), 0 0px 0px rgba(0,0,0,0)',
    };
  };
  const focusTransition = { duration: 0.4, ease: [0.4, 0, 0.2, 1] };

  return (
    <div className="bg-surface dark:bg-slate-950 text-on-surface dark:text-slate-200 selection:bg-primary-container selection:text-on-primary-container relative">
      <div className="dark:block hidden">
        <StarField />
      </div>
      {/* Top Navigation Shell */}
      <nav className="bg-[#f7f9fb]/80 dark:bg-slate-950/80 backdrop-blur-xl top-0 sticky z-50 shadow-sm shadow-slate-200/50 dark:shadow-none font-['Manrope'] antialiased tracking-tight">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center w-full">
          <div className="text-xl font-bold tracking-tighter text-slate-900 dark:text-slate-50">FintrixAi</div>
          <div className="hidden md:flex items-center gap-x-6 lg:gap-x-8">
            <a className="text-slate-900 dark:text-white font-semibold border-b-2 border-slate-900 dark:border-slate-50 pb-1 hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#problem-statement">About Us</a>
            <Link to="/solutions" className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300">Solutions</Link>
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#trust-pipeline">Trust Pipeline</a>
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#intelligence">Compliance</a>
            <Link to="/docs" className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300">Documentation</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link to="/user-status" className="text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-primary transition-colors border border-slate-200 dark:border-slate-700 px-4 py-2 rounded-lg hidden lg:block">Applicant Login</Link>
            <Link to="/manager-login" className="text-sm font-semibold text-white bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 shadow-md transition-colors px-4 py-2 rounded-lg">Manager Portal</Link>
            <Link to="/solutions" className="gradient-cta text-white px-5 py-2 rounded-lg font-semibold active:scale-95 transition-transform duration-200">Request Demo</Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        {/* SECTION 1: HERO */}
        <section className="relative pt-24 pb-32 overflow-hidden bg-surface dark:bg-slate-950/85">
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="lg:col-span-7"
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container-high dark:bg-slate-900 text-on-surface-variant dark:text-slate-400 text-xs font-bold uppercase tracking-widest mb-8">
                <span className="w-2 h-2 rounded-full bg-tertiary"></span>
                Architectural Credit Intelligence
              </div>
              <h1 className="text-5xl lg:text-7xl font-headline font-extrabold text-[#0F172A] dark:text-slate-50 tracking-tighter leading-[1.1] mb-8">
                Credit decisions that <span className="text-tertiary italic">explain</span> themselves.
              </h1>
              <p className="text-xl text-on-surface-variant dark:text-slate-400 font-body leading-relaxed mb-12 max-w-2xl">
                FintrixAi scores NTCs and MSMEs using behavioral signals from bank statements — no credit history required.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
                <Link to="/solutions" className="gradient-cta text-white px-8 py-4 rounded-lg text-lg font-bold shadow-lg shadow-tertiary/25 active:scale-95 transition-transform">Get Started Free</Link>
                <Link to="/docs" className="bg-transparent text-on-surface dark:text-slate-200 px-8 py-4 rounded-lg text-lg font-bold ghost-border active:scale-95 transition-transform">
                  Documentation
                </Link>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.9, rotateY: -10 }}
              whileInView={{ opacity: 1, scale: 1, rotateY: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 1, delay: 0.2 }}
              className="lg:col-span-5 relative"
            >
              <div className="relative z-10 p-8 rounded-3xl bg-[#0F172A] dark:bg-slate-900 shadow-2xl">
                <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-inner">
                  <div className="flex justify-between items-start mb-10">
                    <div>
                      <span className="inline-flex items-center px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-xs font-bold border border-emerald-100 dark:border-emerald-800 mb-3">
                        Grade A — Strong
                      </span>
                      <h4 className="text-3xl font-black text-slate-900 dark:text-white">PD: 4.2%</h4>
                    </div>
                    <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
                      <span className="material-symbols-outlined text-emerald-600 dark:text-emerald-400">verified</span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">SHAP Explainability Tags</p>
                    <div className="flex flex-wrap gap-2">
                      <motion.span
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs font-medium border border-slate-100 dark:border-slate-700 flex items-center gap-1.5"
                      >
                        <span className="text-emerald-500 font-bold">✓</span> Cashflow Stable
                      </motion.span>
                      <motion.span
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs font-medium border border-slate-100 dark:border-slate-700 flex items-center gap-1.5"
                      >
                        <span className="text-emerald-500 font-bold">✓</span> GST Consistent
                      </motion.span>
                      <motion.span
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs font-medium border border-slate-100 dark:border-slate-700 flex items-center gap-1.5"
                      >
                        <span className="text-amber-500 font-bold">⚠</span> High Concentration Risk
                      </motion.span>
                    </div>
                  </div>
                  <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-700">
                    <motion.div
                      animate={{ y: [0, -10, 0], rotate: [0, 1, 0] }}
                      transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                      className="h-2 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden"
                    >
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: "92%" }}
                        transition={{ duration: 1.5, delay: 0.8, ease: "circOut" }}
                        className="h-full bg-emerald-500"
                      ></motion.div>
                    </motion.div>
                    <div className="flex justify-between mt-2 text-[10px] font-bold text-slate-400">
                      <span>CONFIDENCE SCORE</span>
                      <span>92%</span>
                    </div>
                  </div>
                </div>
              </div>
              <motion.div
                animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.3, 0.2] }}
                transition={{ duration: 8, repeat: Infinity }}
                className="absolute -top-12 -right-12 w-64 h-64 bg-tertiary-fixed opacity-20 blur-[100px] rounded-full"
              ></motion.div>
              <motion.div
                animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.4, 0.3] }}
                transition={{ duration: 10, repeat: Infinity, delay: 1 }}
                className="absolute -bottom-12 -left-12 w-64 h-64 bg-primary-container opacity-30 blur-[100px] rounded-full"
              ></motion.div>
            </motion.div>
          </div>
        </section>

        {/* SECTION 2: ₹28 TRILLION BLIND SPOT */}
        <section className="py-24 bg-surface dark:bg-slate-950/85" id="problem-statement">
          <div className="max-w-7xl mx-auto px-6 text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-block px-4 py-1.5 mb-6 rounded-full bg-tertiary-container dark:bg-tertiary-900/30 text-on-tertiary-container dark:text-tertiary-400 text-xs font-bold tracking-widest uppercase font-label">
                The Systemic Crisis
              </div>
              <h2 className="text-5xl md:text-7xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tighter mb-8 leading-[0.9] font-headline">
                The ₹28 Trillion <br /><span className="text-tertiary">Blind Spot.</span>
              </h2>
              <div className="max-w-2xl mx-auto mb-16">
                <p className="text-lg md:text-xl text-on-surface-variant dark:text-slate-400 leading-relaxed font-body">
                  India's financial engine is firing on half its cylinders. A ₹28T gap separates capital from the businesses that need it.
                </p>
              </div>
            </motion.div>

            {/* Impact Grid — outer div handles entry, inner motion.div handles focus */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left items-stretch">
              {[
                { icon: 'groups', val: '450 Million', label: 'Credit-Invisible Individuals', desc: 'A population larger than the United States, ignored by legacy scoring.', highlight: false },
                { icon: 'storefront', val: '63 Million', label: 'Excluded MSMEs', desc: 'Small businesses fueling 30% of GDP, yet starved of working capital.', highlight: false },
                { icon: 'payments', val: '₹28 Trillion', label: 'Systemic Financing Gap', desc: 'The annual capital deficit choking the growth of Emerging India.', highlight: true }
              ].map((card, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 50 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.2, duration: 0.6 }}
                  className="h-full"
                >
                  <motion.div
                    animate={focusAnimate(`impact-${idx}`)}
                    transition={focusTransition}
                    onHoverStart={() => setActiveCard(`impact-${idx}`)}
                    onHoverEnd={() => setActiveCard(null)}
                    className={`group p-8 rounded-lg cursor-pointer h-full ${card.highlight ? 'bg-tertiary text-on-tertiary shadow-xl shadow-tertiary/10' : 'bg-surface-container-lowest dark:bg-slate-900 border border-outline-variant/15 dark:border-slate-800 shadow-sm'}`}
                  >
                    <div className="flex flex-col h-full">
                      <span className={`material-symbols-outlined ${card.highlight ? 'text-white' : 'text-tertiary'} text-4xl mb-6`}>{card.icon}</span>
                      <h3 className={`text-4xl font-black ${card.highlight ? 'text-white' : 'text-slate-900 dark:text-white'} tracking-tight mb-2 font-headline`}>{card.val}</h3>
                      <p className={`${card.highlight ? 'text-tertiary-container' : 'text-on-surface-variant dark:text-slate-400'} font-medium`}>{card.label}</p>
                      <div className={`mt-auto pt-8 border-t ${card.highlight ? 'border-tertiary-fixed-dim/20' : 'border-outline-variant/10 dark:border-slate-800'}`}>
                        <p className={`text-sm ${card.highlight ? 'text-tertiary-container/90' : 'text-on-surface-variant dark:text-slate-400/80'} italic`}>{card.desc}</p>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 4: THE SAFE-BORROWER DEFAULT LOOP */}
        <section className="py-32 bg-surface dark:bg-slate-950/85">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-24 items-start">
              <motion.div
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8 }}
                className="lg:col-span-4 space-y-10"
              >
                <h2 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-50 leading-tight font-headline">
                  The Safe-Borrower <br />Default Loop
                </h2>
                <div className="space-y-8 text-on-surface-variant dark:text-slate-400 leading-relaxed text-lg font-body">
                  <p>
                    Traditional banking institutions are locked in a structural paradox. Bound by rigid credit-score mandates, they prioritize <span className="text-slate-900 dark:text-slate-50 font-semibold underline decoration-tertiary/30 decoration-2">"Safe Borrowers"</span>—those who already have capital.
                  </p>
                  <p>
                    This "Trust Deficit" isn't a lack of reliability; it's a lack of data visibility. Banks are saying no to growth they cannot measure.
                  </p>
                  <p>
                    FintrixAi breaks this cycle by surfacing behavioral reliability through deep forensic analysis of cashflows.
                  </p>
                </div>
              </motion.div>
              <div className="lg:col-span-8 flex flex-col gap-8">
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 }}
                  className="w-full"
                >
                  <h4 className="text-xl font-bold text-slate-900 dark:text-slate-50 mb-4 font-headline uppercase tracking-tight">Gap Paradox Analysis</h4>
                  <div className="bg-surface-container-lowest dark:bg-slate-900 p-10 rounded-2xl shadow-sm border border-outline-variant/10 dark:border-slate-800">
                    <div className="space-y-10">
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm font-bold dark:text-slate-300">
                          <span>FORMAL SUPPLY</span>
                          <span>₹35T</span>
                        </div>
                        <div className="h-6 bg-surface-container-highest dark:bg-slate-800 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ x: "-100%" }}
                            whileInView={{ x: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 1.5, ease: "circOut" }}
                            className="h-full bg-slate-400 w-full rounded-full"
                          ></motion.div>
                        </div>
                      </div>
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm font-bold text-tertiary">
                          <span>UNMET GAP</span>
                          <span>₹28T</span>
                        </div>
                        <div className="h-6 bg-tertiary-container dark:bg-tertiary-900/30 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ x: "-100%" }}
                            whileInView={{ x: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 1.5, delay: 0.3, ease: "circOut" }}
                            className="h-full bg-tertiary w-[80%] rounded-full"
                          ></motion.div>
                        </div>
                      </div>
                    </div>
                    <p className="mt-8 text-sm text-on-surface-variant dark:text-slate-400 font-body">The unmet gap now rivals 80% of the total formal supply volume.</p>
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.4 }}
                  className="w-full"
                >
                  <h4 className="text-xl font-bold text-slate-900 dark:text-slate-50 mb-4 font-headline uppercase tracking-tight">Shrinking Gateway</h4>
                  <div className="bg-[#0F172A] dark:bg-slate-900 p-10 rounded-2xl shadow-xl">
                    <div className="relative h-48 flex items-end justify-between px-4 mb-8">
                      <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                        <motion.path
                          initial={{ pathLength: 0 }}
                          whileInView={{ pathLength: 1 }}
                          viewport={{ once: true }}
                          transition={{ duration: 2, ease: "easeInOut" }}
                          d="M0 20 L25 25 L50 40 L75 55 L100 65" fill="none" stroke="#82ff99" strokeLinecap="round" strokeWidth="4"
                        ></motion.path>
                        <path d="M0 20 L25 25 L50 40 L75 55 L100 65 L100 100 L0 100 Z" fill="url(#grad-landing)" opacity="0.1"></path>
                        <defs>
                          <linearGradient id="grad-landing" x1="0%" x2="0%" y1="0%" y2="100%">
                            <stop offset="0%" stopColor="#82ff99" stopOpacity="1"></stop>
                            <stop offset="100%" stopColor="#82ff99" stopOpacity="0"></stop>
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="z-10 text-center">
                        <span className="block text-4xl font-black text-white">21%</span>
                        <span className="block text-xs text-slate-500 dark:text-slate-400 font-bold mt-2">DEC 23</span>
                      </div>
                      <div className="z-10 text-center">
                        <span className="block text-4xl font-black text-tertiary-fixed">17%</span>
                        <span className="block text-xs text-slate-500 dark:text-slate-400 font-bold mt-2">DEC 24</span>
                      </div>
                    </div>
                    <div className="pt-6 border-t border-slate-800">
                      <p className="text-sm text-slate-400 mb-1 font-body">NTC Inclusion Trend</p>
                      <h4 className="text-xl font-bold text-white tracking-tight font-headline">Access is tightening, not expanding.</h4>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5: TRUST PIPELINE */}
        <section className="py-32 bg-surface-container-low dark:bg-slate-900/50" id="trust-pipeline">
          <div className="max-w-7xl mx-auto px-6">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="mb-20"
            >
              <h2 className="text-4xl font-headline font-bold text-[#0F172A] dark:text-slate-50 mb-6">The Trust Pipeline</h2>
              <p className="text-lg text-on-surface-variant dark:text-slate-400 font-body max-w-2xl">A proprietary four-stage architectural framework designed to transform raw financial noise into high-fidelity credit signals.</p>
            </motion.div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch">
              {[
                { step: 'Data Ingestion', icon: 'database', color: '#3B82F6', desc: 'Collect and standerdize financial data(bank statement, GST, bills etc) using Account Aggregator-Ready pipeline.' },
                { step: 'Trust Intelligence Layer(Fraud Filter)', icon: 'shield', color: '#EF4444', desc: 'Detecting circular transaction fraud, synthetic balance inflation and suspicious manual altering of bank statements' },
                { step: 'Hybrid Scoring Layer', icon: 'psychology', color: '#8B5CF6', desc: 'XGBoost + Bayesian Modeling and multiple features (payment history, utility discipline etc) to calculate credit risk (Probability of Default).' },
                { step: 'Explainable AI Layer (Output & Transparency)', icon: 'bar_chart', color: '#22C55E', desc: 'Generates human-readable reasons (via SHAP) for each decision, ensuring regulatory compliance and trust in the system.' }
              ].map((item, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.15 }}
                  className="h-full"
                >
                  <motion.div
                    animate={focusAnimate(`pipeline-${idx}`)}
                    transition={focusTransition}
                    onHoverStart={() => setActiveCard(`pipeline-${idx}`)}
                    onHoverEnd={() => setActiveCard(null)}
                    style={{ borderLeftColor: item.color }}
                    className="bg-surface-container-lowest dark:bg-slate-900 p-10 rounded-2xl border-l-[4px] cursor-pointer flex flex-col h-full"
                  >
                    <div className="w-14 h-14 rounded-full flex items-center justify-center mb-8" style={{ backgroundColor: `${item.color}1a` }}>
                      <span className="material-symbols-outlined" style={{ color: item.color }}>{item.icon}</span>
                    </div>
                    <h3 className="font-headline font-bold text-2xl dark:text-slate-50 mb-4">{item.step}</h3>
                    <p className="text-base text-on-surface-variant dark:text-slate-400 leading-relaxed">{item.desc}</p>
                  </motion.div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 6: INTELLIGENCE BEYOND THE LEDGER */}
        <section className="py-32 bg-surface dark:bg-slate-950/85" id="intelligence">
          <div className="max-w-7xl mx-auto px-6">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="flex flex-col md:flex-row justify-between items-end gap-8 mb-20"
            >
              <div className="max-w-2xl">
                <h2 className="text-4xl font-headline font-extrabold text-[#0F172A] dark:text-slate-50 mb-6 tracking-tight">Intelligence Beyond the Ledger</h2>
                <p className="text-lg text-on-surface-variant dark:text-slate-400">Standard bureau reports miss 60% of the small business economy. Our features capture the "invisible" indicators of intent and resilience.</p>
              </div>
            </motion.div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
              {[
                { label: 'Grade A Strong', title: 'Psychometric Risk Analysis', desc: 'Proprietary logic that maps repayment behavior against seasonal volatility to determine borrower "character" under stress.', color: 'bg-tertiary', val: '80%', textColor: 'text-tertiary' },
                { label: 'Grade C Watch', title: 'Cashflow Integrity', desc: 'Isolation of true revenue from loan churn, intra-day reversals, and suspicious inward remittances.', color: 'bg-amber-500', val: '50%', textColor: 'text-amber-600' },
                { label: 'Grade E Risk', title: 'Fraud Loop Detection', desc: 'AI-driven mapping of connected party transactions to detect hidden leverage across multiple legal entities.', color: 'bg-error', val: '25%', textColor: 'text-error' }
              ].map((feature, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.95 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.3 }}
                  className="h-full"
                >
                  <motion.div
                    animate={focusAnimate(`intel-${idx}`)}
                    transition={focusTransition}
                    onHoverStart={() => setActiveCard(`intel-${idx}`)}
                    onHoverEnd={() => setActiveCard(null)}
                    className="p-10 bg-surface-container-lowest dark:bg-slate-900 rounded-lg border border-outline-variant/15 dark:border-slate-800 cursor-pointer h-full flex flex-col"
                  >
                    <h4 className={`text-xs font-bold uppercase tracking-[0.2em] ${feature.textColor} mb-6`}>{feature.label}</h4>
                    <h3 className="text-2xl font-headline font-bold text-[#0F172A] dark:text-slate-50 mb-4">{feature.title}</h3>
                    <p className="text-on-surface-variant dark:text-slate-400 leading-relaxed mb-8">{feature.desc}</p>
                    <div className="h-1 w-full bg-surface-container dark:bg-slate-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: feature.val }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, delay: 0.5 + (idx * 0.2) }}
                        className={`h-full ${feature.color}`}
                      ></motion.div>
                    </div>
                  </motion.div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* EXPLORE DEMO PROFILES */}
        <section className="py-20 bg-surface-container-low dark:bg-slate-900/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="max-w-3xl mx-auto px-6 text-center"
          >
            <h2 className="text-2xl md:text-3xl font-headline font-bold text-slate-700 dark:text-slate-300 tracking-tight mb-4">Explore Demo Profiles</h2>
            <p className="text-base text-on-surface-variant dark:text-slate-400 leading-relaxed mb-8 max-w-xl mx-auto">
              See how FintrixAi scores different borrower archetypes — from salaried professionals to seasonal farmers to fraud cases.
            </p>
            <Link to="/demo" className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-sm border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-600 active:scale-95 transition-all duration-200 group">
              See Demo Profiles
              <motion.span
                animate={{ x: [0, 4, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="material-symbols-outlined text-base"
              >arrow_forward</motion.span>
            </Link>
          </motion.div>
        </section>

        {/* FOOTER / BOTTOM CTA */}
        <section className="bg-[#0F172A] dark:bg-black py-24">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="max-w-7xl mx-auto px-6 text-center"
          >
            <h2 className="text-4xl md:text-5xl font-headline font-extrabold text-white mb-6 tracking-tight">Ready to score your first application?</h2>
            <Link to="/demo" className="gradient-cta text-white px-12 py-5 rounded-xl text-xl font-bold font-headline tracking-tight hover:bg-tertiary-dim transition-all duration-300 shadow-2xl shadow-tertiary/20 flex items-center gap-4 mx-auto mb-8 active:scale-95 w-fit">
              Access Risk Scoring →
            </Link>
            <p className="text-slate-400 text-lg font-medium font-body max-w-xl mx-auto mb-4">
              No credit history required. Upload a bank statement and get a risk grade in seconds.
            </p>
            <Link to="/demo" className="text-slate-500 dark:text-slate-400 text-xs underline">
              View Demo Profiles
            </Link>
          </motion.div>
        </section>
      </main>
    </div>
  );
}

export default LandingPage;
