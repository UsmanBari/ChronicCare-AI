"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Language, translations, Translations } from "../translations";
import { isFirebaseEnabled, getFirebaseAuth } from "../lib/firebase";
import { getRoleFromEmail } from "../lib/roles";
import { onAuthStateChanged, signOut } from "firebase/auth";
import {
  api,
  subscribeServerWaking,
  ProfileResponse,
  EHRConnectionResponse,
  CheckinStartResponse,
  CheckinCompleteResponse,
} from "../lib/api";

export type PortalType = "landing" | "patient" | "provider" | "admin";

export type PatientScreenType =
  | "login"
  | "consent"
  | "connection"
  | "profile"
  | "home"
  | "checkin_entry"
  | "adaptive_interview"
  | "confirmation"
  | "processing"
  | "risk_result"
  | "trends"
  | "conflict_detail"
  | "conflict_review"
  | "emergency"
  | "appointments";

export type ProviderScreenType =
  | "login"
  | "dashboard"
  | "review_queue"
  | "reconciliation_alert"
  | "patient_detail"
  | "schedule_appointment";

export type AdminScreenType = "login" | "dashboard";

export type ConnectionMode = "fhir" | "offline" | null;
export type MissedMedsOption = "yes" | "no" | "prefer_not_to_answer" | null;
export type RiskLevel = "low" | "moderate" | "high";
export type DemoScenario = "normal" | "conflict" | "emergency" | "ehr_update";

export interface HealthProfile {
  conditions: string[];
  medications: string[];
  age: string;
}

export interface CheckInData {
  note: string;
  thirst: boolean | null;
  urination: boolean | null;
  missedMeds: MissedMedsOption;
  lowConfidence: boolean;
  submittedAt: string | null;
}

export interface AppointmentState {
  isBooked: boolean;
  slot: string;
  reason: string;
  provider: string;
  status: string;
  bookedAt: string;
}

interface AppContextType {
  // Portals
  portal: PortalType;
  setPortal: (p: PortalType) => void;

  // Patient Screen state
  screen: PatientScreenType;
  setScreen: (screen: PatientScreenType) => void;

  // Provider Screen state
  providerScreen: ProviderScreenType;
  setProviderScreen: (screen: ProviderScreenType) => void;

  // Admin Screen state
  adminScreen: AdminScreenType;
  setAdminScreen: (screen: AdminScreenType) => void;

  // Unified Settings toggle
  showSettings: boolean;
  setShowSettings: (show: boolean) => void;

  // Evaluator Tour Modal toggle
  showTour: boolean;
  setShowTour: (show: boolean) => void;

  // Selected patient in Provider Portal
  selectedPatient: string | null;
  setSelectedPatient: (patient: string | null) => void;

  // Language & Translations
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
  isUrdu: boolean;

  // Auth identifiers & roles
  userIdentifier: string;
  setUserIdentifier: (id: string) => void;
  providerIdentifier: string;
  setProviderIdentifier: (id: string) => void;
  adminIdentifier: string;
  setAdminIdentifier: (id: string) => void;
  userRole: string | null;
  setUserRole: (role: string | null) => void;

  // Live Mode & Cloud states
  isLiveMode: boolean;
  serverWaking: boolean;
  liveProfile: ProfileResponse | null;
  setLiveProfile: React.Dispatch<React.SetStateAction<ProfileResponse | null>>;
  liveEhrConnection: EHRConnectionResponse | null;
  setLiveEhrConnection: React.Dispatch<React.SetStateAction<EHRConnectionResponse | null>>;
  activeLiveCheckin: CheckinStartResponse | null;
  setActiveLiveCheckin: React.Dispatch<React.SetStateAction<CheckinStartResponse | null>>;
  liveCheckinResult: CheckinCompleteResponse | null;
  setLiveCheckinResult: React.Dispatch<React.SetStateAction<CheckinCompleteResponse | null>>;
  escalationRecorded: boolean | null;
  setEscalationRecorded: React.Dispatch<React.SetStateAction<boolean | null>>;
  refreshLiveState: () => Promise<void>;

  // Connection mode
  connectionMode: ConnectionMode;
  setConnectionMode: (mode: ConnectionMode) => void;

  // Patient profile & check-in
  profile: HealthProfile;
  setProfile: React.Dispatch<React.SetStateAction<HealthProfile>>;
  checkIn: CheckInData;
  setCheckIn: React.Dispatch<React.SetStateAction<CheckInData>>;

  // Shared appointment state across Patient & Provider
  appointment: AppointmentState;
  setAppointment: React.Dispatch<React.SetStateAction<AppointmentState>>;

  // Provider actions state
  resolvedCases: string[];
  resolveCase: (patientName: string) => void;
  acknowledgedPatients: string[];
  acknowledgePatient: (patientName: string) => void;

  // Presenter Controls (demo scenario)
  demoScenario: DemoScenario;
  setDemoScenario: (scenario: DemoScenario) => void;

  // Clean navigation helpers
  returnToHomeAndClearRun: () => void;
  resetDemo: () => void;
  signOutUser: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [portal, setPortalState] = useState<PortalType>("landing");
  const [screen, setScreenState] = useState<PatientScreenType>("home");
  const [providerScreen, setProviderScreenState] = useState<ProviderScreenType>("dashboard");
  const [adminScreen, setAdminScreenState] = useState<AdminScreenType>("dashboard");
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [showTour, setShowTour] = useState<boolean>(false);
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);

  const [language, setLanguage] = useState<Language>("en");
  const [userIdentifier, setUserIdentifier] = useState<string>("ali.khan@demo.care");
  const [providerIdentifier, setProviderIdentifier] = useState<string>("dr.sanamalik@citygeneral.org");
  const [adminIdentifier, setAdminIdentifier] = useState<string>("admin@citygeneral.org");
  const [userRole, setUserRole] = useState<string | null>(null);
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>("fhir");

  // Live Mode states
  const isLiveMode = isFirebaseEnabled();
  const [serverWaking, setServerWaking] = useState<boolean>(false);
  const [liveProfile, setLiveProfile] = useState<ProfileResponse | null>(null);
  const [liveEhrConnection, setLiveEhrConnection] = useState<EHRConnectionResponse | null>(null);
  const [activeLiveCheckin, setActiveLiveCheckin] = useState<CheckinStartResponse | null>(null);
  const [liveCheckinResult, setLiveCheckinResult] = useState<CheckinCompleteResponse | null>(null);
  const [escalationRecorded, setEscalationRecorded] = useState<boolean | null>(null);

  // Single-flight promise refs for authSession
  const sessionPromiseRef = React.useRef<Promise<any> | null>(null);
  const sessionUserUidRef = React.useRef<string | null>(null);

  // Presenter controls
  const [demoScenario, setDemoScenario] = useState<DemoScenario>("normal");

  // Patient Baseline Profile (Mock mode fallback)
  const [profile, setProfile] = useState<HealthProfile>({
    conditions: ["Type 2 Diabetes"],
    medications: [
      "Metformin 500mg (1+1)",
      "Lisinopril 10mg (1+0)",
      "Atorvastatin 20mg (0+1)",
      "Aspirin 81mg (1+0)",
    ],
    age: "58",
  });

  // Transient check-in data
  const [checkIn, setCheckIn] = useState<CheckInData>({
    note: "",
    thirst: null,
    urination: null,
    missedMeds: null,
    lowConfidence: false,
    submittedAt: null,
  });

  // Shared Appointment state
  const [appointment, setAppointment] = useState<AppointmentState>({
    isBooked: false,
    slot: "",
    reason: "",
    provider: "Dr. Sana Malik",
    status: "Confirmed",
    bookedAt: "",
  });

  // Provider review actions
  const [resolvedCases, setResolvedCases] = useState<string[]>([]);
  const [acknowledgedPatients, setAcknowledgedPatients] = useState<string[]>([]);

  // Server Waking Subscription
  useEffect(() => {
    const unsubscribe = subscribeServerWaking((isWaking) => {
      setServerWaking(isWaking);
    });
    return () => unsubscribe();
  }, []);

  // Browser History & Back/Forward Button Navigation Synchronization
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (!window.history.state) {
      window.history.replaceState(
        { portal: "landing", screen: "home", providerScreen: "dashboard", adminScreen: "dashboard" },
        ""
      );
    }

    const handlePopState = (event: PopStateEvent) => {
      if (event.state) {
        const { portal: p, screen: s, providerScreen: ps, adminScreen: as } = event.state;
        if (p) setPortalState(p);
        if (s) setScreenState(s);
        if (ps) setProviderScreenState(ps);
        if (as) setAdminScreenState(as);
      } else {
        setPortalState("landing");
        setScreenState("home");
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const pushNavState = (
    nextPortal: PortalType,
    nextScreen: PatientScreenType,
    nextProviderScreen: ProviderScreenType,
    nextAdminScreen: AdminScreenType
  ) => {
    if (typeof window !== "undefined") {
      window.history.pushState(
        {
          portal: nextPortal,
          screen: nextScreen,
          providerScreen: nextProviderScreen,
          adminScreen: nextAdminScreen,
        },
        ""
      );
    }
  };

  const refreshLiveState = async () => {
    if (!isLiveMode) return;
    try {
      const prof = await api.getProfile();
      setLiveProfile(prof);
      if (prof.language && (prof.language === "en" || prof.language === "ur")) {
        setLanguage(prof.language as Language);
      }
    } catch {
      // Ignore if not initialized
    }

    try {
      const conn = await api.getEHRConnection();
      setLiveEhrConnection(conn);
      if (conn.mode === "fhir" || conn.mode === "isolated") {
        setConnectionMode(conn.mode === "fhir" ? "fhir" : "offline");
      }
    } catch {
      // Ignore if not initialized
    }
  };

  // Synchronize Firebase Auth State across browser refreshes
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (!isLiveMode) {
      // Mock mode: Keep default demo state
      return;
    }

    const auth = getFirebaseAuth();
    if (!auth) return;

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user && user.email) {
        const email = user.email;

        // In LIVE mode: role comes strictly from /api/auth/session or /api/me
        // Single-flight promise: avoid calling /api/auth/session multiple times per sign-in
        try {
          if (!sessionPromiseRef.current || sessionUserUidRef.current !== user.uid) {
            sessionUserUidRef.current = user.uid;
            sessionPromiseRef.current = api.authSession();
          }
          const session = await sessionPromiseRef.current;
          const role = session.role;
          setUserRole(role);

          // Role gating against the active portal:
          if (portal === "patient") {
            if (role !== "patient") {
              await signOut(auth);
              setUserRole(null);
              setScreenState("login");
              return;
            }
            setUserIdentifier(email);
            // Check consent status for patient
            try {
              const prof = await api.getProfile();
              setLiveProfile(prof);
              if (!prof.consent_granted_at) {
                setScreenState("consent");
              }
            } catch {
              setScreenState("consent");
            }
          } else if (portal === "provider") {
            if (role !== "provider" && role !== "admin") {
              await signOut(auth);
              setUserRole(null);
              setProviderScreenState("login");
              return;
            }
            setProviderIdentifier(email);
          } else if (portal === "admin") {
            if (role !== "admin") {
              await signOut(auth);
              setUserRole(null);
              setAdminScreenState("login");
              return;
            }
            setAdminIdentifier(email);
          }
        } catch (err) {
          // Backend communication error or invalid token: fail-closed
          sessionPromiseRef.current = null;
          sessionUserUidRef.current = null;
          try {
            await signOut(auth);
          } catch {}
          setUserRole(null);
        }
      } else {
        sessionPromiseRef.current = null;
        sessionUserUidRef.current = null;
        setUserRole(null);
      }
    });

    return () => unsubscribe();
  }, [portal, isLiveMode]);

  const signOutUser = async () => {
    sessionPromiseRef.current = null;
    sessionUserUidRef.current = null;
    if (isLiveMode) {
      const auth = getFirebaseAuth();
      if (auth) {
        try {
          await signOut(auth);
        } catch {
          // Silent catch
        }
      }
    }
    setUserRole(null);
    setLiveProfile(null);
    setLiveEhrConnection(null);
    setActiveLiveCheckin(null);
    setLiveCheckinResult(null);
    setEscalationRecorded(null);
  };

  const setPortal = (p: PortalType) => {
    if (p === "landing") {
      signOutUser().catch(() => {});
    }
    setPortalState(p);
    pushNavState(p, screen, providerScreen, adminScreen);
  };

  const setScreen = (s: PatientScreenType) => {
    setScreenState(s);
    pushNavState(portal, s, providerScreen, adminScreen);
  };

  const setProviderScreen = (ps: ProviderScreenType) => {
    setProviderScreenState(ps);
    pushNavState(portal, screen, ps, adminScreen);
  };

  const setAdminScreen = (as: AdminScreenType) => {
    setAdminScreenState(as);
    pushNavState(portal, screen, providerScreen, as);
  };

  const resolveCase = (patientName: string) => {
    if (!resolvedCases.includes(patientName)) {
      setResolvedCases((prev) => [...prev, patientName]);
    }
  };

  const acknowledgePatient = (patientName: string) => {
    if (!acknowledgedPatients.includes(patientName)) {
      setAcknowledgedPatients((prev) => [...prev, patientName]);
    }
  };

  const t = translations[language];
  const isUrdu = language === "ur";

  const returnToHomeAndClearRun = () => {
    setScreenState("home");
    pushNavState(portal, "home", providerScreen, adminScreen);
    setCheckIn({
      note: "",
      thirst: null,
      urination: null,
      missedMeds: null,
      lowConfidence: false,
      submittedAt: null,
    });
    setActiveLiveCheckin(null);
    setLiveCheckinResult(null);
    setEscalationRecorded(null);
  };

  const resetDemo = () => {
    signOutUser().catch(() => {});
    setDemoScenario("normal");
    setScreenState("home");
    pushNavState("patient", "home", "dashboard", "dashboard");
    setCheckIn({
      note: "",
      thirst: null,
      urination: null,
      missedMeds: null,
      lowConfidence: false,
      submittedAt: null,
    });
    setResolvedCases([]);
    setAcknowledgedPatients([]);
    setAppointment({
      isBooked: false,
      slot: "",
      reason: "",
      provider: "Dr. Sana Malik",
      status: "Confirmed",
      bookedAt: "",
    });
    setActiveLiveCheckin(null);
    setLiveCheckinResult(null);
    setEscalationRecorded(null);
  };

  return (
    <AppContext.Provider
      value={{
        portal,
        setPortal,
        screen,
        setScreen,
        providerScreen,
        setProviderScreen,
        adminScreen,
        setAdminScreen,
        showSettings,
        setShowSettings,
        showTour,
        setShowTour,
        selectedPatient,
        setSelectedPatient,
        language,
        setLanguage,
        t,
        isUrdu,
        userIdentifier,
        setUserIdentifier,
        providerIdentifier,
        setProviderIdentifier,
        adminIdentifier,
        setAdminIdentifier,
        userRole,
        setUserRole,
        isLiveMode,
        serverWaking,
        liveProfile,
        setLiveProfile,
        liveEhrConnection,
        setLiveEhrConnection,
        activeLiveCheckin,
        setActiveLiveCheckin,
        liveCheckinResult,
        setLiveCheckinResult,
        escalationRecorded,
        setEscalationRecorded,
        refreshLiveState,
        connectionMode,
        setConnectionMode,
        profile,
        setProfile,
        checkIn,
        setCheckIn,
        appointment,
        setAppointment,
        resolvedCases,
        resolveCase,
        acknowledgedPatients,
        acknowledgePatient,
        demoScenario,
        setDemoScenario,
        returnToHomeAndClearRun,
        resetDemo,
        signOutUser,
      }}
    >
      <div dir={isUrdu ? "rtl" : "ltr"} className={isUrdu ? "font-urdu" : "font-sans"}>
        {/* Server Waking Notification Bar (Live Mode Only) */}
        {serverWaking && (
          <div className="fixed top-0 left-0 right-0 z-50 bg-amber-600 text-white px-4 py-2.5 text-center text-xs sm:text-sm font-semibold shadow-lg flex items-center justify-center gap-2 animate-fadeIn">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-200 animate-ping" />
            <span>{t.serverWakingTitle}</span>
          </div>
        )}
        {children}
      </div>
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
