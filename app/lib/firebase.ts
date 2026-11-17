import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import { getAuth, Auth, GoogleAuthProvider, signInWithPopup, signInWithRedirect, UserCredential } from "firebase/auth";

let firebaseAppInstance: FirebaseApp | null = null;
let firebaseAuthInstance: Auth | null = null;

const GLOBAL_APP_KEY = "__CHRONICARE_FIREBASE_APP__";
const GLOBAL_AUTH_KEY = "__CHRONICARE_FIREBASE_AUTH__";

export function isFirebaseEnabled(): boolean {
  return process.env.NEXT_PUBLIC_AUTH_MODE === "firebase";
}

export function isFirebaseConfigured(): boolean {
  const config = getFirebaseConfig();
  return Boolean(config.apiKey && config.projectId);
}

export function getFirebaseConfig() {
  return {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "",
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
  };
}

/**
 * Lazily initializes and returns the Firebase Auth instance.
 * Safe to import and call anywhere: returns null if auth mode is not "firebase" or if config is missing.
 * Guarded against duplicate initialization.
 */
export function getFirebaseAuth(): Auth | null {
  if (typeof window === "undefined") {
    return null;
  }

  if (!isFirebaseEnabled()) {
    return null;
  }

  const config = getFirebaseConfig();
  if (!config.apiKey || !config.projectId) {
    return null;
  }

  // Cross-chunk singleton protection: retrieve from window if available
  const globalObj = typeof window !== "undefined" ? (window as any) : (globalThis as any);
  if (globalObj[GLOBAL_AUTH_KEY]) {
    firebaseAuthInstance = globalObj[GLOBAL_AUTH_KEY];
    return firebaseAuthInstance;
  }

  if (!firebaseAuthInstance) {
    if (!getApps().length) {
      firebaseAppInstance = initializeApp(config);
    } else {
      firebaseAppInstance = getApp();
    }
    firebaseAuthInstance = getAuth(firebaseAppInstance);
  }

  if (globalObj) {
    globalObj[GLOBAL_APP_KEY] = firebaseAppInstance;
    globalObj[GLOBAL_AUTH_KEY] = firebaseAuthInstance;
  }

  return firebaseAuthInstance;
}

export function getAuthErrorMessage(
  errorCode: string,
  t: {
    authInvalidApiKey: string;
    authUserNotFound: string;
    authWrongPassword: string;
    authInvalidCredentials: string;
    authEmailAlreadyInUse?: string;
    authWeakPassword?: string;
    authTooManyRequests?: string;
    authNetworkError?: string;
    authInvalidEmail?: string;
    authGeneralError: string;
    [key: string]: any;
  }
): string {
  switch (errorCode) {
    case "auth/invalid-api-key":
    case "auth/api-key-not-valid":
      return t.authInvalidApiKey;
    case "auth/user-not-found":
    case "auth/wrong-password":
    case "auth/invalid-credential":
    case "auth/invalid-login-credentials":
      return t.authInvalidCredentials || t.authWrongPassword || t.authUserNotFound;
    case "auth/invalid-email":
      return t.authInvalidEmail || t.authInvalidCredentials;
    case "auth/email-already-in-use":
      return t.authEmailAlreadyInUse || t.authGeneralError;
    case "auth/weak-password":
      return t.authWeakPassword || t.authGeneralError;
    case "auth/too-many-requests":
      return t.authTooManyRequests || t.authGeneralError;
    case "auth/network-request-failed":
      return t.authNetworkError || t.authGeneralError;
    case "auth/operation-not-allowed":
      return "Google sign-in is not enabled in Firebase Console";
    case "auth/account-exists-with-different-credential":
      return "An account already exists with this email using a different sign-in method";
    case "auth/unauthorized-domain":
      return "This domain is not authorized in Firebase Console";
    case "auth/popup-blocked":
      return "Pop-up blocked. Please allow pop-ups for this site and retry.";
    default:
      return t.authGeneralError;
  }
}

/**
 * Initiates Google sign-in using Firebase GoogleAuthProvider and signInWithPopup.
 * Falls back to signInWithRedirect if popup is blocked, or handles popup closed gracefully.
 * Uses the cached Firebase Auth instance.
 */
export async function signInWithGoogle(): Promise<{ userCredential?: UserCredential; cancelled?: boolean; error?: string }> {
  if (!isFirebaseEnabled()) {
    return { error: "Google sign-in is available in Firebase mode only." };
  }
  const auth = getFirebaseAuth();
  if (!auth) {
    return { error: "Firebase authentication is not configured." };
  }

  const provider = new GoogleAuthProvider();
  try {
    const cred = await signInWithPopup(auth, provider);
    return { userCredential: cred };
  } catch (err: any) {
    const code = err?.code || "";
    if (code === "auth/popup-closed-by-user") {
      return { cancelled: true };
    }
    if (code === "auth/operation-not-allowed") {
      return { error: "Google sign-in is not enabled in Firebase Console" };
    }
    if (code === "auth/account-exists-with-different-credential") {
      return { error: "An account already exists with this email using a different sign-in method" };
    }
    if (code === "auth/unauthorized-domain") {
      return { error: "This domain is not authorized in Firebase Console" };
    }
    if (code === "auth/popup-blocked") {
      try {
        await signInWithRedirect(auth, provider);
        return { cancelled: true };
      } catch {
        return { error: "Pop-up blocked. Please allow pop-ups for this site and retry." };
      }
    }
    return { error: err?.message || "Google sign-in failed. Please try again." };
  }
}


