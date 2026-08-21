import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './AuthContext';

export default function NavUser() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = async () => {
    setOpen(false);
    await logout();
    navigate('/login');
  };

  // Not logged in — show Login button
  if (!user) {
    return (
      <Link
        to="/login"
        className="text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:hover:text-white transition-all duration-300"
      >
        Login
      </Link>
    );
  }

  // Initials fallback if no photo
  const initials = (user.name || user.email || '?')
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 rounded-full pl-1 pr-3 py-1 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-200 active:scale-95"
      >
        {user.photo ? (
          <img src={user.photo} alt={user.name} className="w-8 h-8 rounded-full object-cover ring-2 ring-emerald-500/40" />
        ) : (
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white text-xs font-bold ring-2 ring-emerald-500/40">
            {initials}
          </div>
        )}
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200 max-w-[120px] truncate hidden sm:block">
          {user.name?.split(' ')[0] || user.email}
        </span>
        <span className="material-symbols-outlined text-slate-400 text-base">
          {open ? 'expand_less' : 'expand_more'}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className="absolute right-0 mt-2 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-xl shadow-black/10 dark:shadow-black/40 z-50 overflow-hidden"
          >
            {/* Profile header */}
            <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                {user.photo ? (
                  <img src={user.photo} alt={user.name} className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center text-white text-sm font-bold">
                    {initials}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{user.name || 'User'}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user.email}</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 text-xs bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 rounded-full px-2.5 py-0.5 font-medium">
                  <span className="material-symbols-outlined text-xs">verified</span>
                  {user.role || 'User'}
                </span>
                {user.provider === 'google' && (
                  <span className="inline-flex items-center gap-1 text-xs bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20 rounded-full px-2.5 py-0.5 font-medium">
                    Google
                  </span>
                )}
              </div>
            </div>

            {/* Menu items */}
            <div className="p-2">
              <Link
                to="/solutions"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <span className="material-symbols-outlined text-slate-400 text-xl">analytics</span>
                Assessment Tool
              </Link>
              <Link
                to="/demo"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <span className="material-symbols-outlined text-slate-400 text-xl">people</span>
                Demo Profiles
              </Link>

              <div className="my-1.5 border-t border-slate-100 dark:border-slate-800" />

              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors text-left"
              >
                <span className="material-symbols-outlined text-red-400 text-xl">logout</span>
                Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
