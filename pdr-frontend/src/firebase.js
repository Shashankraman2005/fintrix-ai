import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyC1olWKY1hDrOu4WPbZ1SqbshNv_MoLtYQ",
  authDomain: "paise-do-re.firebaseapp.com",
  projectId: "paise-do-re",
  storageBucket: "paise-do-re.firebasestorage.app",
  messagingSenderId: "980972773145",
  appId: "1:980972773145:web:a1a15b8aea5f493f516f88",
  measurementId: "G-1B81TT8ZS3"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
