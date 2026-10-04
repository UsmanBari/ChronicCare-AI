import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import { getAuth, Auth } from "firebase/auth";

let firebaseAppInstance: FirebaseApp | null = null;
let firebaseAuthInstance: Auth | null = null;

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

  if (!firebaseAuthInstance) {
    if (!getApps().length) {
      firebaseAppInstance = initializeApp(config);
    } else {
      firebaseAppInstance = getApp();
    }
    firebaseAuthInstance = getAuth(firebaseAppInstance);
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
    authGeneralError: string;
  }
): string {
  switch (errorCode) {
    case "auth/invalid-api-key":
    case "auth/api-key-not-valid":
      return t.authInvalidApiKey;
    case "auth/user-not-found":
      return t.authUserNotFound;
    case "auth/wrong-password":
      return t.authWrongPassword;
    case "auth/invalid-credential":
    case "auth/invalid-login-credentials":
    case "auth/invalid-email":
      return t.authInvalidCredentials;
    default:
      return t.authGeneralError;
  }
}

