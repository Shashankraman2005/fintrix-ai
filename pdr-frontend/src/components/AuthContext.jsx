import React, { createContext, useContext, useState, useEffect } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = loading, null = logged out

  useEffect(() => {
    // Listen for Firebase (Google) auth changes
    const unsub = onAuthStateChanged(auth, (firebaseUser) => {
      if (firebaseUser) {
        setUser({
          email: firebaseUser.email,
          name: firebaseUser.displayName || firebaseUser.email,
          photo: firebaseUser.photoURL,
          role: 'Loan Officer',
          provider: 'google',
        });
      } else {
        // Fall back to localStorage for email/password users
        const stored = localStorage.getItem('fintrixai_auth') || localStorage.getItem('pdr_auth');
        if (stored) {
          try {
            const parsed = JSON.parse(stored);
            setUser({ ...parsed, provider: 'local' });
          } catch {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      }
    });
    return unsub;
  }, []);

  const logout = async () => {
    await signOut(auth);
    localStorage.removeItem('fintrixai_auth');
    localStorage.removeItem('pdr_auth');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
