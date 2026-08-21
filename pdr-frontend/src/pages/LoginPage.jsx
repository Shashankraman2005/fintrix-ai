import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import StarField from '../components/StarField';
import ThemeToggle from '../components/ThemeToggle';

// Demo credentials — replace with real auth when backend is ready
const DEMO_USERS = [
  { email: 'officer@fintrixai.ai', password: 'pdr2025', role: 'Loan Officer', redirect: '/solutions' },
  { email: 'demo@fintrixai.ai',    password: 'demo123',  role: 'Demo User',    redirect: '/demo' },
  { email: 'officer@pdr.ai', password: 'pdr2025', role: 'Loan Officer', redirect: '/solutions' },
  { email: 'demo@pdr.ai',    password: 'demo123',  role: 'Demo User',    redirect: '/demo' },
];

const ROLES = ['Loan Officer', 'Credit Analyst', 'Branch Manager', 'Risk Officer'];

const cardVariants = {
  initial: (dir) => ({ opacity: 0, x: dir * 40 }),
  animate: { opacity: 1, x: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
  exit:    (dir) => ({ opacity: 0, x: dir * -40, transition: { duration: 0.25, ease: [0.4, 0, 1, 1] } }),
};

function InputField({ icon, label, type = 'text', value, onChange, placeholder, autoComplete, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
      <div className="relative">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl">{icon}</span>
        <input
          type={type}
          required
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full bg-slate-800/60 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-all duration-200 text-sm"
        />
        {children}
      </div>
    </div>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [dir, setDir]   = useState(1);       // slide direction

  // Login state
  const [loginEmail, setLoginEmail]       = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPass, setShowLoginPass] = useState(false);
  const [loginError, setLoginError]       = useState('');
  const [loginLoading, setLoginLoading]   = useState(false);

  // Signup state
  const [signupName, setSignupName]           = useState('');
  const [signupEmail, setSignupEmail]         = useState('');
  const [signupRole, setSignupRole]           = useState(ROLES[0]);
  const [signupPassword, setSignupPassword]   = useState('');
  const [signupConfirm, setSignupConfirm]     = useState('');
  const [showSignupPass, setShowSignupPass]   = useState(false);
  const [signupError, setSignupError]         = useState('');
  const [signupLoading, setSignupLoading]     = useState(false);
  const [signupSuccess, setSignupSuccess]     = useState(false);

  const switchTo = (next) => {
    setDir(next === 'signup' ? 1 : -1);
    setMode(next);
    setLoginError('');
    setSignupError('');
    setSignupSuccess(false);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    await new Promise(r => setTimeout(r, 700));

    const email = loginEmail.trim().toLowerCase();

    // Check hardcoded demo users first
    const demoMatch = DEMO_USERS.find(u => u.email === email && u.password === loginPassword);
    if (demoMatch) {
      localStorage.setItem('fintrixai_auth', JSON.stringify({ email: demoMatch.email, role: demoMatch.role }));
      localStorage.setItem('pdr_auth', JSON.stringify({ email: demoMatch.email, role: demoMatch.role }));
      navigate(demoMatch.redirect);
      return;
    }

    // Check locally registered users (from sign-up form)
    const registered = JSON.parse(localStorage.getItem('fintrixai_registered_users') || localStorage.getItem('pdr_registered_users') || '[]');
    const regMatch = registered.find(u => u.email === email && u.password === loginPassword);
    if (regMatch) {
      localStorage.setItem('fintrixai_auth', JSON.stringify({ email: regMatch.email, role: regMatch.role, name: regMatch.name }));
      localStorage.setItem('pdr_auth', JSON.stringify({ email: regMatch.email, role: regMatch.role, name: regMatch.name }));
      navigate('/solutions');
      return;
    }

    setLoginError('Invalid email or password.');
    setLoginLoading(false);
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setSignupError('');

    if (signupPassword.length < 8) {
      setSignupError('Password must be at least 8 characters.');
      return;
    }
    if (signupPassword !== signupConfirm) {
      setSignupError('Passwords do not match.');
      return;
    }

    setSignupLoading(true);
    await new Promise(r => setTimeout(r, 900));

    // Store in localStorage as a registered user (demo — no real backend)
    const existing = JSON.parse(localStorage.getItem('fintrixai_registered_users') || localStorage.getItem('pdr_registered_users') || '[]');
    if (existing.find(u => u.email === signupEmail.trim().toLowerCase())) {
      setSignupError('An account with this email already exists.');
      setSignupLoading(false);
      return;
    }
    existing.push({ name: signupName, email: signupEmail.trim().toLowerCase(), role: signupRole, password: signupPassword });
    localStorage.setItem('fintrixai_registered_users', JSON.stringify(existing));
    localStorage.setItem('pdr_registered_users', JSON.stringify(existing));

    setSignupLoading(false);
    setSignupSuccess(true);
  };

  const handleGoogleSignIn = async () => {
    setLoginError('');
    setLoginLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      localStorage.setItem('fintrixai_auth', JSON.stringify({
        email: user.email,
        role: 'Loan Officer',
        name: user.displayName,
        photo: user.photoURL,
      }));
      localStorage.setItem('pdr_auth', JSON.stringify({
        email: user.email,
        role: 'Loan Officer',
        name: user.displayName,
        photo: user.photoURL,
      }));
      navigate('/solutions');
    } catch (err) {
      setLoginError(err.code === 'auth/popup-closed-by-user' ? 'Sign-in cancelled.' : 'Google sign-in failed. Try again.');
      setLoginLoading(false);
    }
  };

  const fillDemo = (user) => {
    setLoginEmail(user.email);
    setLoginPassword(user.password);
    setLoginError('');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col relative overflow-hidden">
      <StarField />

      {/* Nav */}
      <nav className="relative z-10 flex justify-between items-center px-8 py-5">
        <Link to="/" className="text-xl font-bold tracking-tighter text-white">
          FintrixAi
        </Link>
        <ThemeToggle />
      </nav>

      {/* Center card */}
      <div className="flex-1 flex items-center justify-center px-4 py-10 relative z-10">
        <div className="w-full max-w-md relative">

          {/* Glow blob */}
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Mode toggle pill */}
          <div className="relative flex bg-slate-900/60 border border-slate-800 rounded-xl p-1 mb-4 backdrop-blur-xl">
            <motion.div
              className="absolute top-1 bottom-1 rounded-lg bg-emerald-600/20 border border-emerald-500/30"
              animate={{ left: mode === 'login' ? '4px' : '50%', right: mode === 'login' ? '50%' : '4px' }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            />
            {['login', 'signup'].map(m => (
              <button
                key={m}
                onClick={() => switchTo(m)}
                className={`relative flex-1 py-2 text-sm font-semibold rounded-lg transition-colors duration-200 ${
                  mode === m ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {m === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Card */}
          <div className="relative bg-slate-900/80 border border-slate-800 backdrop-blur-xl rounded-2xl shadow-2xl shadow-black/60 overflow-hidden">
            <AnimatePresence mode="wait" custom={dir}>
              {mode === 'login' ? (
                <motion.div
                  key="login"
                  custom={dir}
                  variants={cardVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="p-10"
                >
                  {/* Header */}
                  <div className="mb-7 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-4">
                      <span className="material-symbols-outlined text-emerald-400 text-2xl">shield_person</span>
                    </div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">Welcome back</h1>
                    <p className="text-slate-400 text-sm mt-1">Sign in to your FintrixAi account</p>
                  </div>

                  {/* Quick-fill */}
                  <div className="flex gap-2 mb-6">
                    {DEMO_USERS.map(u => (
                      <button
                        key={u.email}
                        type="button"
                        onClick={() => fillDemo(u)}
                        className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-700 text-slate-400 hover:border-emerald-500/50 hover:text-emerald-400 hover:bg-emerald-500/5 transition-all duration-200"
                      >
                        <span className="material-symbols-outlined text-base align-middle mr-1">bolt</span>
                        {u.role}
                      </button>
                    ))}
                  </div>

                  <form onSubmit={handleLogin} className="space-y-5">
                    <InputField icon="mail" label="Email" type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="officer@fintrixai.ai" autoComplete="email" />

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl">lock</span>
                        <input
                          type={showLoginPass ? 'text' : 'password'}
                          required
                          autoComplete="current-password"
                          value={loginPassword}
                          onChange={e => setLoginPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full bg-slate-800/60 border border-slate-700 rounded-xl pl-10 pr-12 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-all duration-200 text-sm"
                        />
                        <button type="button" onClick={() => setShowLoginPass(p => !p)}
                          className="absolute right-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 hover:text-slate-300 transition-colors text-xl">
                          {showLoginPass ? 'visibility_off' : 'visibility'}
                        </button>
                      </div>
                    </div>

                    <AnimatePresence>
                      {loginError && (
                        <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                          className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                          <span className="material-symbols-outlined text-base">error</span>
                          {loginError}
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <button type="submit" disabled={loginLoading}
                      className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all duration-200 active:scale-95">
                      {loginLoading ? (
                        <><span className="material-symbols-outlined text-base animate-spin">progress_activity</span>Signing in...</>
                      ) : (
                        <>Sign in<span className="material-symbols-outlined text-base">arrow_forward</span></>
                      )}
                    </button>

                    {/* Divider */}
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-px bg-slate-800" />
                      <span className="text-xs text-slate-600">or</span>
                      <div className="flex-1 h-px bg-slate-800" />
                    </div>

                    {/* Google */}
                    <button
                      type="button"
                      onClick={handleGoogleSignIn}
                      disabled={loginLoading}
                      className="w-full flex items-center justify-center gap-3 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700 hover:border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-all duration-200 active:scale-95 text-sm"
                    >
                      <svg className="w-5 h-5 shrink-0" viewBox="0 0 48 48">
                        <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.6 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
                        <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13 24 13c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
                        <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.3 35.2 26.8 36 24 36c-5.3 0-9.7-3.4-11.3-8H6.4C9.8 35.6 16.4 44 24 44z"/>
                        <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.3 5.6l6.2 5.2C36.9 40.8 44 35 44 24c0-1.3-.1-2.6-.4-3.9z"/>
                      </svg>
                      Continue with Google
                    </button>
                  </form>

                  <p className="text-center text-sm text-slate-500 mt-6">
                    No account?{' '}
                    <button onClick={() => switchTo('signup')} className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
                      Create one
                    </button>
                  </p>
                </motion.div>

              ) : (
                <motion.div
                  key="signup"
                  custom={dir}
                  variants={cardVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="p-10"
                >
                  <div className="mb-7 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-4">
                      <span className="material-symbols-outlined text-emerald-400 text-2xl">person_add</span>
                    </div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">Create account</h1>
                    <p className="text-slate-400 text-sm mt-1">Join the FintrixAi Credit Intelligence Platform</p>
                  </div>

                  <AnimatePresence mode="wait">
                    {signupSuccess ? (
                      <motion.div
                        key="success"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="text-center py-6"
                      >
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 mb-4">
                          <span className="material-symbols-outlined text-emerald-400 text-4xl">check_circle</span>
                        </div>
                        <h2 className="text-white font-bold text-lg mb-2">Account created!</h2>
                        <p className="text-slate-400 text-sm mb-6">Your account is pending approval by an administrator.</p>
                        <button
                          onClick={() => switchTo('login')}
                          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 py-2.5 rounded-xl transition-all duration-200 active:scale-95 text-sm"
                        >
                          <span className="material-symbols-outlined text-base">login</span>
                          Go to Sign In
                        </button>
                      </motion.div>
                    ) : (
                      <motion.form key="form" onSubmit={handleSignup} className="space-y-4">
                        <InputField icon="person" label="Full Name" value={signupName} onChange={e => setSignupName(e.target.value)} placeholder="Priya Venkataraman" autoComplete="name" />
                        <InputField icon="mail" label="Work Email" type="email" value={signupEmail} onChange={e => setSignupEmail(e.target.value)} placeholder="you@bank.com" autoComplete="email" />

                        {/* Role select */}
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-1.5">Role</label>
                          <div className="relative">
                            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl">badge</span>
                            <select
                              value={signupRole}
                              onChange={e => setSignupRole(e.target.value)}
                              className="w-full bg-slate-800/60 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-all duration-200 text-sm appearance-none"
                            >
                              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl pointer-events-none">expand_more</span>
                          </div>
                        </div>

                        {/* Password */}
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
                          <div className="relative">
                            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl">lock</span>
                            <input
                              type={showSignupPass ? 'text' : 'password'}
                              required
                              autoComplete="new-password"
                              value={signupPassword}
                              onChange={e => setSignupPassword(e.target.value)}
                              placeholder="Min. 8 characters"
                              className="w-full bg-slate-800/60 border border-slate-700 rounded-xl pl-10 pr-12 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-all duration-200 text-sm"
                            />
                            <button type="button" onClick={() => setShowSignupPass(p => !p)}
                              className="absolute right-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 hover:text-slate-300 transition-colors text-xl">
                              {showSignupPass ? 'visibility_off' : 'visibility'}
                            </button>
                          </div>
                          {/* Password strength bar */}
                          {signupPassword.length > 0 && (
                            <div className="mt-2 flex gap-1">
                              {[1,2,3,4].map(i => (
                                <div key={i} className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                                  signupPassword.length >= i * 3
                                    ? i <= 1 ? 'bg-red-500' : i <= 2 ? 'bg-amber-500' : i <= 3 ? 'bg-blue-500' : 'bg-emerald-500'
                                    : 'bg-slate-700'
                                }`} />
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Confirm password */}
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                          <div className="relative">
                            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-500 text-xl">lock_reset</span>
                            <input
                              type="password"
                              required
                              autoComplete="new-password"
                              value={signupConfirm}
                              onChange={e => setSignupConfirm(e.target.value)}
                              placeholder="Repeat password"
                              className={`w-full bg-slate-800/60 border rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-1 transition-all duration-200 text-sm ${
                                signupConfirm && signupConfirm !== signupPassword
                                  ? 'border-red-500/60 focus:border-red-500 focus:ring-red-500/30'
                                  : signupConfirm && signupConfirm === signupPassword
                                  ? 'border-emerald-500/60 focus:border-emerald-500 focus:ring-emerald-500/30'
                                  : 'border-slate-700 focus:border-emerald-500 focus:ring-emerald-500/50'
                              }`}
                            />
                            {signupConfirm && (
                              <span className={`absolute right-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-base ${
                                signupConfirm === signupPassword ? 'text-emerald-400' : 'text-red-400'
                              }`}>
                                {signupConfirm === signupPassword ? 'check_circle' : 'cancel'}
                              </span>
                            )}
                          </div>
                        </div>

                        <AnimatePresence>
                          {signupError && (
                            <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                              className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                              <span className="material-symbols-outlined text-base">error</span>
                              {signupError}
                            </motion.div>
                          )}
                        </AnimatePresence>

                        <button type="submit" disabled={signupLoading}
                          className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all duration-200 active:scale-95 !mt-5">
                          {signupLoading ? (
                            <><span className="material-symbols-outlined text-base animate-spin">progress_activity</span>Creating account...</>
                          ) : (
                            <>Create account<span className="material-symbols-outlined text-base">arrow_forward</span></>
                          )}
                        </button>

                        {/* Divider */}
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-px bg-slate-800" />
                          <span className="text-xs text-slate-600">or</span>
                          <div className="flex-1 h-px bg-slate-800" />
                        </div>

                        {/* Google */}
                        <button
                          type="button"
                          onClick={handleGoogleSignIn}
                          disabled={signupLoading}
                          className="w-full flex items-center justify-center gap-3 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700 hover:border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-all duration-200 active:scale-95 text-sm"
                        >
                          <svg className="w-5 h-5 shrink-0" viewBox="0 0 48 48">
                            <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.6 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
                            <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13 24 13c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
                            <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.3 35.2 26.8 36 24 36c-5.3 0-9.7-3.4-11.3-8H6.4C9.8 35.6 16.4 44 24 44z"/>
                            <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.3 5.6l6.2 5.2C36.9 40.8 44 35 44 24c0-1.3-.1-2.6-.4-3.9z"/>
                          </svg>
                          Sign up with Google
                        </button>
                      </motion.form>
                    )}
                  </AnimatePresence>

                  {!signupSuccess && (
                    <p className="text-center text-sm text-slate-500 mt-5">
                      Already have an account?{' '}
                      <button onClick={() => switchTo('login')} className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
                        Sign in
                      </button>
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <p className="text-center text-xs text-slate-700 mt-5">
            FintrixAi Credit Intelligence · For authorised loan officers only
          </p>
        </div>
      </div>
    </div>
  );
}
