import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, ArrowRight } from 'lucide-react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import StarField from '../components/StarField';

export default function ManagerPortal() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    try {
      setLoading(true);
      setError('');
      // Authenticate with Google
      const result = await signInWithPopup(auth, googleProvider);
      if (result.user) {
        // In a real app, we'd check if result.user.email is an authorized manager email
        // For this prototype, we'll let any authenticated Google user into the dashboard.
        navigate('/manager-dashboard');
      }
    } catch (err) {
      console.error(err);
      setError('Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-slate-950 flex items-center justify-center overflow-hidden">
      <StarField />
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md p-8 bg-surface/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl"
      >
        <div className="flex flex-col items-center mb-10 text-center">
          <div className="w-16 h-16 bg-primary/20 text-primary rounded-full flex items-center justify-center mb-4 border border-primary/50">
            <Shield size={32} />
          </div>
          <h1 className="text-3xl font-headline font-bold text-white mb-2">Manager Portal</h1>
          <p className="text-slate-400">Secure access for loan officers</p>
        </div>

        <div className="space-y-6">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 text-slate-800 font-bold py-3 px-4 rounded-xl transition-all shadow-lg focus:ring-4 focus:ring-white/30"
          >
            {loading ? (
              <div className="w-6 h-6 border-2 border-slate-400 border-t-slate-800 rounded-full animate-spin"></div>
            ) : (
              <>
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" className="w-6 h-6" />
                Sign in with Google
              </>
            )}
          </button>
          
          {error && <p className="text-sm text-center text-red-400 bg-red-500/10 py-2 rounded-lg border border-red-500/20">{error}</p>}
        </div>

        <div className="mt-8 pt-6 border-t border-white/10 text-center flex flex-col gap-2">
          <p className="text-sm text-slate-400">Not a loan officer?</p>
          <div className="flex justify-center gap-4">
            <button onClick={() => navigate('/')} className="text-primary hover:text-white transition-colors text-sm font-medium">Main Website</button>
            <span className="text-slate-600">•</span>
            <button onClick={() => navigate('/user-status')} className="text-primary hover:text-white transition-colors text-sm font-medium">Applicant Login</button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
