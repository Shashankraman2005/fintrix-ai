import React from 'react';
import './Landing.css';

function Landing({ onStart }) {
  return (
    <div className="bg-surface text-on-surface dark:text-slate-200 selection:bg-primary-container selection:text-on-primary-container font-body">
      {/* Top Navigation Shell */}
      <nav className="bg-[#f7f9fb]/80 dark:bg-slate-950/80 backdrop-blur-xl docked full-width top-0 sticky z-50 shadow-sm shadow-slate-200/50 dark:shadow-none font-['Manrope'] antialiased tracking-tight">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center w-full">
          <div className="text-xl font-bold tracking-tighter text-slate-900 dark:text-slate-50">FintrixAi</div>
          <div className="hidden md:flex items-center space-gap-8 gap-x-8">
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#problem-statement">About Us</a>
            <a className="text-slate-900 dark:text-white font-semibold border-b-2 border-slate-900 dark:border-slate-50 pb-1 hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#problem-statement">Solutions</a>
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#trust-pipeline">Trust Pipeline</a>
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="#intelligence">Compliance</a>
            <a className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300" href="/docs">Documentation</a>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-[#565e74] dark:text-slate-300 font-medium hover:text-slate-900 dark:text-white dark:hover:text-white transition-all duration-300 active:scale-95">Login</button>
            <button onClick={onStart} className="gradient-primary text-on-primary px-6 py-2.5 rounded-lg font-semibold active:scale-95 transition-transform duration-200">Request Demo</button>
          </div>
        </div>
      </nav>
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-32 overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
            <div className="lg:col-span-7">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container-high text-on-surface-variant dark:text-slate-400 text-xs font-bold uppercase tracking-widest mb-8">
                <span className="w-2 h-2 rounded-full bg-tertiary"></span>
                Architectural Credit Intelligence
              </div>
              <h1 className="text-5xl lg:text-7xl font-headline font-extrabold text-[#0F172A] tracking-tighter leading-[1.1] mb-8">
                Credit decisions that <span className="text-primary dark:text-white italic">explain</span> themselves.
              </h1>
              <p className="text-xl text-on-surface-variant dark:text-slate-400 font-body leading-relaxed mb-12 max-w-2xl">
                FintrixAi scores NTCs and MSMEs using behavioral signals from bank statements — no credit history required. Transition from binary approvals to nuanced risk intelligence.
              </p>
              <div className="flex flex-wrap gap-4">
                <button onClick={onStart} className="gradient-primary text-on-primary px-8 py-4 rounded-lg text-lg font-bold flex items-center gap-2 shadow-lg shadow-primary/20 active:scale-95 transition-transform">
                  View Demo Profiles
                  <span className="material-symbols-outlined">arrow_forward</span>
                </button>
                <a href="/docs" className="bg-surface-container-high text-on-surface dark:text-slate-200 px-8 py-4 rounded-lg text-lg font-bold ghost-border active:scale-95 transition-transform text-center inline-block">
                  Documentation
                </a>
              </div>
            </div>
            <div className="lg:col-span-5 relative">
              <div className="relative z-10 rounded-lg overflow-hidden shadow-2xl shadow-slate-200/50">
                <img className="w-full h-auto" data-alt="Modern minimalist dashboard" src="https://lh3.googleusercontent.com/aida-public/AB6AXuA2oNjvphduYcZ9Xjv3g-izCeXAtup-mBqKcw1TXuH_DjaYlb4hWAIwIimyG6fVyQQpq9VC6-rWPP4FjbLS3Wxonz6WqeQ_vMt1kVn_EYlUAKmvSKvK6xhWHEc6D5YPGmO6wbk0KoU5sxEAwo1c-_FK2mYg1_Gv1eXM5aJVxSeHShgvRAjw0VXlsRYKHRDhcvFlB91IMwiuYb69T6uAzkT5LcpzpIPkyW-hyibTJZ3kbdhtvjaq9DhJXnpf3TolUboOdEfL621NAA" alt="Dashboard preview"/>
              </div>
              <div className="absolute -top-12 -right-12 w-64 h-64 bg-tertiary-fixed opacity-20 blur-[100px] rounded-full"></div>
              <div className="absolute -bottom-12 -left-12 w-64 h-64 bg-primary-container opacity-30 blur-[100px] rounded-full"></div>
            </div>
          </div>
        </section>

        {/* Problem Statement Section */}
        <section className="py-24 bg-surface border-t border-outline-variant/10" id="problem-statement">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-24">
              <div className="inline-block px-4 py-1.5 mb-6 rounded-full bg-tertiary-container text-on-tertiary-container text-xs font-bold tracking-widest uppercase font-label">
                The Systemic Crisis
              </div>
              <h2 className="text-5xl md:text-7xl font-extrabold text-slate-900 dark:text-white tracking-tighter mb-8 leading-[0.9] font-headline">
                The ₹28 Trillion <br/><span className="text-tertiary">Blind Spot.</span>
              </h2>
              <div className="max-w-2xl mx-auto">
                <p className="text-lg md:text-xl text-on-surface-variant dark:text-slate-400 leading-relaxed font-body">
                  India's financial engine is firing on half its cylinders. While formal markets thrive, a vast segment of the economy remains invisible to traditional risk models, creating a chasm between potential and capital.
                </p>
              </div>
            </div>

            {/* Impact Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-32">
              {/* Card 1 */}
              <div className="group p-8 rounded-lg bg-surface-container-lowest border border-outline-variant/15 hover:border-tertiary/40 transition-all duration-500 shadow-sm">
                <div className="flex flex-col h-full">
                  <span className="material-symbols-outlined text-tertiary text-4xl mb-6">groups</span>
                  <h3 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight mb-2 font-headline">450 Million</h3>
                  <p className="text-on-surface-variant dark:text-slate-400 font-medium">Credit-Invisible Individuals</p>
                  <div className="mt-auto pt-8 border-t border-outline-variant/10">
                    <p className="text-sm text-on-surface-variant dark:text-slate-400/80 italic">A population larger than the United States, ignored by legacy scoring.</p>
                  </div>
                </div>
              </div>
              {/* Card 2 */}
              <div className="group p-8 rounded-lg bg-surface-container-lowest border border-outline-variant/15 hover:border-tertiary/40 transition-all duration-500 shadow-sm">
                <div className="flex flex-col h-full">
                  <span className="material-symbols-outlined text-tertiary text-4xl mb-6">storefront</span>
                  <h3 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight mb-2 font-headline">63 Million</h3>
                  <p className="text-on-surface-variant dark:text-slate-400 font-medium">Excluded MSMEs</p>
                  <div className="mt-auto pt-8 border-t border-outline-variant/10">
                    <p className="text-sm text-on-surface-variant dark:text-slate-400/80 italic">Small businesses fueling 30% of GDP, yet starved of working capital.</p>
                  </div>
                </div>
              </div>
              {/* Card 3 */}
              <div className="group p-8 rounded-lg bg-tertiary text-on-tertiary transition-all duration-500 shadow-xl shadow-tertiary/10">
                <div className="flex flex-col h-full">
                  <span className="material-symbols-outlined text-white text-4xl mb-6">payments</span>
                  <h3 className="text-4xl font-black text-white tracking-tight mb-2 font-headline">₹28 Trillion</h3>
                  <p className="text-tertiary-container font-medium">Systemic Financing Gap</p>
                  <div className="mt-auto pt-8 border-t border-tertiary-fixed-dim/20">
                    <p className="text-sm text-tertiary-container/90 italic">The annual capital deficit choking the growth of Emerging India.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Narrative & Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-start mb-32">
              {/* Narrative Column */}
              <div className="lg:col-span-5 space-y-10">
                <h2 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight font-headline">
                  The Safe-Borrower <br/>Default Loop
                </h2>
                <div className="space-y-6 text-on-surface-variant dark:text-slate-400 leading-relaxed text-lg font-body">
                  <p>
                    Traditional banking institutions are locked in a structural paradox. Bound by rigid credit-score mandates, they prioritize <span className="text-slate-900 dark:text-white font-semibold underline decoration-tertiary/30 decoration-2">"Safe Borrowers"</span>—those who already have capital—while neglecting the most productive segments of the emerging workforce.
                  </p>
                  <p>
                    This "Trust Deficit" isn't a lack of reliability; it's a lack of data visibility. Banks aren't just saying no to risk; they are saying no to growth they cannot measure.
                  </p>
                </div>
                <div className="p-6 rounded-md bg-surface-container-high/50 border-l-4 border-tertiary">
                  <p className="text-sm font-semibold text-on-surface dark:text-slate-200 italic font-body">
                    "The largest risk is not the default of one person, but the structural exclusion of 450 million productive citizens."
                  </p>
                </div>
              </div>

              {/* Visual Column (Bento-style Charts) */}
              <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Gap Paradox Bar Chart */}
                <div className="bg-surface-container-lowest p-8 rounded-lg shadow-sm border border-outline-variant/10 flex flex-col justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant dark:text-slate-400 mb-6 font-label">Gap Paradox Analysis</p>
                    <div className="space-y-8">
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs font-bold mb-1">
                          <span>FORMAL SUPPLY</span>
                          <span>₹35T</span>
                        </div>
                        <div className="h-4 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className="h-full bg-slate-400 w-full rounded-full"></div>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs font-bold mb-1 text-tertiary">
                          <span>UNMET GAP</span>
                          <span>₹28T</span>
                        </div>
                        <div className="h-4 bg-tertiary-container rounded-full overflow-hidden">
                          <div className="h-full bg-tertiary w-[80%] rounded-full"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="mt-8 text-xs text-on-surface-variant dark:text-slate-400 leading-tight font-body">The unmet gap now rivals 80% of the total formal supply volume.</p>
                </div>

                {/* Shrinking Gateway Trend Line */}
                <div className="bg-[#0F172A] p-8 rounded-lg shadow-xl flex flex-col justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-6 font-label">Shrinking Gateway</p>
                    <div className="relative h-32 flex items-end justify-between px-2">
                      <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                        <path d="M0 20 L25 25 L50 40 L75 55 L100 65" fill="none" stroke="#82ff99" strokeLinecap="round" strokeWidth="3"></path>
                        <path d="M0 20 L25 25 L50 40 L75 55 L100 65 L100 100 L0 100 Z" fill="url(#grad)" opacity="0.1"></path>
                        <defs>
                          <linearGradient id="grad" x1="0%" x2="0%" y1="0%" y2="100%">
                            <stop offset="0%" stopColor="#82ff99" stopOpacity="1"></stop>
                            <stop offset="100%" stopColor="#82ff99" stopOpacity="0"></stop>
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="z-10 text-center">
                        <span className="block text-2xl font-black text-white">21%</span>
                        <span className="block text-[10px] text-slate-500 dark:text-slate-400 font-bold">DEC 23</span>
                      </div>
                      <div className="z-10 text-center">
                        <span className="block text-2xl font-black text-tertiary-fixed">17%</span>
                        <span className="block text-[10px] text-slate-500 dark:text-slate-400 font-bold">DEC 24</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-8">
                    <p className="text-xs text-slate-400 mb-1 font-body">NTC Inclusion Trend</p>
                    <h4 className="text-lg font-bold text-white tracking-tight font-headline">Access is tightening, not expanding.</h4>
                  </div>
                </div>
              </div>
            </div>

            {/* CTA Section */}
            <div className="flex flex-col items-center">
              <a className="group bg-tertiary text-on-tertiary px-12 py-6 rounded-full text-xl font-bold font-headline tracking-tight hover:bg-tertiary-dim transition-all duration-300 shadow-2xl shadow-tertiary/20 flex items-center gap-4 active:scale-95" href="#proposed-solution">
                Explore the Trust-Gated Solution
                <span className="material-symbols-outlined group-hover:translate-x-2 transition-transform">arrow_forward</span>
              </a>
              <p className="mt-6 text-on-surface-variant dark:text-slate-400/60 text-sm font-medium font-body">Join FintrixAi in re-architecting the ledger of trust.</p>
            </div>
          </div>
        </section>

        {/* The Proposed Solution */}
        <div id="proposed-solution">
          {/* The 4-Layer Trust Pipeline */}
          <section className="py-24 bg-surface-container-low">
            <div className="max-w-7xl mx-auto px-6">
              <div className="mb-20">
                <h2 className="text-3xl font-headline font-bold text-[#0F172A] mb-4">The Trust Pipeline</h2>
                <p className="text-on-surface-variant dark:text-slate-400 font-body max-w-xl">A proprietary four-stage architectural framework designed to transform raw financial noise into high-fidelity credit signals.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Step 1 */}
                <div className="bg-surface-container-lowest p-8 rounded-lg ghost-border hover:shadow-xl transition-shadow duration-500">
                  <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-primary dark:text-white">input</span>
                  </div>
                  <h3 className="font-headline font-bold text-xl mb-3">Ingest</h3>
                  <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed">Multi-source bank statement aggregation via OCR and API connectors with 99.8% field accuracy.</p>
                </div>
                {/* Step 2 */}
                <div className="bg-surface-container-lowest p-8 rounded-lg ghost-border hover:shadow-xl transition-shadow duration-500">
                  <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-primary dark:text-white">security_update_good</span>
                  </div>
                  <h3 className="font-headline font-bold text-xl mb-3">Forensics</h3>
                  <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed">Deep-level behavioral analysis detecting circulation, round-tripping, and synthetic balance inflation.</p>
                </div>
                {/* Step 3 */}
                <div className="bg-surface-container-lowest p-8 rounded-lg ghost-border hover:shadow-xl transition-shadow duration-500">
                  <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-primary dark:text-white">query_stats</span>
                  </div>
                  <h3 className="font-headline font-bold text-xl mb-3">XGBoost</h3>
                  <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed">Gradient boosting decision trees predicting probability of default based on 450+ non-traditional features.</p>
                </div>
                {/* Step 4 */}
                <div className="bg-surface-container-lowest p-8 rounded-lg ghost-border hover:shadow-xl transition-shadow duration-500 border-l-4 border-tertiary">
                  <div className="w-12 h-12 rounded-full bg-tertiary-container flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>verified_user</span>
                  </div>
                  <h3 className="font-headline font-bold text-xl mb-3">SHAP</h3>
                  <p className="text-sm text-on-surface-variant dark:text-slate-400 leading-relaxed">The "Explainability Engine" - decomposing every score into local feature contributions for regulatory transparency.</p>
                </div>
              </div>
            </div>
          </section>

          {/* Alternative Scoring Features */}
          <section className="py-32">
            <div className="max-w-7xl mx-auto px-6">
              <div className="flex flex-col md:flex-row justify-between items-end gap-8 mb-20">
                <div className="max-w-2xl">
                  <h2 className="text-4xl font-headline font-extrabold text-[#0F172A] mb-6 tracking-tight">Intelligence Beyond the Ledger</h2>
                  <p className="text-lg text-on-surface-variant dark:text-slate-400">Standard bureau reports miss 60% of the small business economy. Our features capture the "invisible" indicators of intent and resilience.</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Feature 1 */}
                <div className="group p-10 bg-surface-container-lowest rounded-lg ghost-border hover:bg-surface-bright transition-colors">
                  <h4 className="text-xs font-bold uppercase tracking-[0.2em] text-tertiary mb-6">Grade A Strong</h4>
                  <h3 className="text-2xl font-headline font-bold text-[#0F172A] mb-4">Psychometric Risk Analysis</h3>
                  <p className="text-on-surface-variant dark:text-slate-400 leading-relaxed mb-8">Proprietary logic that maps repayment behavior against seasonal volatility to determine borrower "character" under stress.</p>
                  <div className="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-tertiary w-4/5"></div>
                  </div>
                </div>
                {/* Feature 2 */}
                <div className="group p-10 bg-surface-container-lowest rounded-lg ghost-border hover:bg-surface-bright transition-colors">
                  <h4 className="text-xs font-bold uppercase tracking-[0.2em] text-amber-600 mb-6">Grade C Watch</h4>
                  <h3 className="text-2xl font-headline font-bold text-[#0F172A] mb-4">Cashflow Integrity</h3>
                  <p className="text-on-surface-variant dark:text-slate-400 leading-relaxed mb-8">Isolation of true revenue from loan churn, intra-day reversals, and suspicious inward remittances.</p>
                  <div className="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 w-1/2"></div>
                  </div>
                </div>
                {/* Feature 3 */}
                <div className="group p-10 bg-surface-container-lowest rounded-lg ghost-border hover:bg-surface-bright transition-colors">
                  <h4 className="text-xs font-bold uppercase tracking-[0.2em] text-error mb-6">Grade E Risk</h4>
                  <h3 className="text-2xl font-headline font-bold text-[#0F172A] mb-4">Fraud Loop Detection</h3>
                  <p className="text-on-surface-variant dark:text-slate-400 leading-relaxed mb-8">AI-driven mapping of connected party transactions to detect hidden leverage across multiple legal entities.</p>
                  <div className="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-error w-1/4"></div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default Landing;
