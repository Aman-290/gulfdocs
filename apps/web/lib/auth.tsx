"use client";

import {
  GoogleAuthProvider,
  User,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
} from "firebase/auth";
import { getApp, getApps, initializeApp } from "firebase/app";
import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type GulfDocsUser = {
  displayName: string;
  email: string | null;
  mode: "development" | "firebase";
};

type AuthContextValue = {
  user: GulfDocsUser | null;
  loading: boolean;
  firebaseConfigured: boolean;
  getToken: () => Promise<string | null>;
  signInLocal: (name: string) => void;
  signInGoogle: () => Promise<void>;
  signInEmail: (
    email: string,
    password: string,
    create: boolean,
  ) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const LOCAL_AUTH_KEY = "gulfdocs.development-user";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const firebaseConfigured = Object.values(firebaseConfig).every(Boolean);

function normalizedFirebaseUser(user: User): GulfDocsUser {
  return {
    displayName: user.displayName || user.email?.split("@")[0] || "Reviewer",
    email: user.email,
    mode: "firebase",
  };
}

function firebaseAuth() {
  if (!firebaseConfigured) {
    throw new Error(
      "Firebase authentication is not configured for this environment.",
    );
  }
  const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  return getAuth(app);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<GulfDocsUser | null>(null);
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (firebaseConfigured) {
      return onAuthStateChanged(firebaseAuth(), (nextUser) => {
        setFirebaseUser(nextUser);
        setUser(nextUser ? normalizedFirebaseUser(nextUser) : null);
        setLoading(false);
      });
    }
    const localName = window.localStorage.getItem(LOCAL_AUTH_KEY);
    queueMicrotask(() => {
      if (localName && process.env.NODE_ENV !== "production") {
        setUser({
          displayName: localName,
          email: `${localName}@local.invalid`,
          mode: "development",
        });
      }
      setLoading(false);
    });
  }, []);

  const getToken = useCallback(async () => {
    if (firebaseUser) return firebaseUser.getIdToken();
    if (user?.mode === "development") return `dev:${user.displayName}`;
    return null;
  }, [firebaseUser, user]);

  const signInLocal = useCallback((name: string) => {
    if (process.env.NODE_ENV === "production") {
      throw new Error("Development authentication is disabled in production.");
    }
    const safeName = name
      .trim()
      .replace(/[^a-zA-Z0-9_-]/g, "-")
      .slice(0, 80);
    if (!safeName) throw new Error("Enter a valid development identity.");
    window.localStorage.setItem(LOCAL_AUTH_KEY, safeName);
    setUser({
      displayName: safeName,
      email: `${safeName}@local.invalid`,
      mode: "development",
    });
  }, []);

  const signInGoogle = useCallback(async () => {
    await signInWithPopup(firebaseAuth(), new GoogleAuthProvider());
  }, []);

  const signInEmail = useCallback(
    async (email: string, password: string, create: boolean) => {
      const auth = firebaseAuth();
      if (create) await createUserWithEmailAndPassword(auth, email, password);
      else await signInWithEmailAndPassword(auth, email, password);
    },
    [],
  );

  const signOut = useCallback(async () => {
    window.localStorage.removeItem(LOCAL_AUTH_KEY);
    if (firebaseConfigured) await firebaseSignOut(firebaseAuth());
    setFirebaseUser(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      firebaseConfigured,
      getToken,
      signInLocal,
      signInGoogle,
      signInEmail,
      signOut,
    }),
    [getToken, loading, signInEmail, signInGoogle, signInLocal, signOut, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
