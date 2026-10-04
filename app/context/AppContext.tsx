"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Language, translations, Translations } from "../translations";
import { isFirebaseEnabled, getFirebaseAuth } from "../lib/firebase";
import { getRoleFromEmail } from "../lib/roles";
import { onAuthStateChanged, signOut } from "firebase/auth";

export type PortalType = "landing" | "patient" | "provider" | "admin";

export type PatientScreenType =
  | "login"
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

  // Auth identifiers
  userIdentifier: string;
  setUserIdentifier: (id: string) => void;
  providerIdentifier: string;
  setProviderIdentifier: (id: string) => void;
  adminIdentifier: string;
  setAdminIdentifier: (id: string) => void;

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
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>("fhir");

  // Presenter controls
  const [demoScenario, setDemoScenario] = useState<DemoScenario>("normal");

  // Patient Baseline Profile
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

  // Browser History & Back/Forward Button Navigation Synchronization
  React.useEffect(() => {
    if (typeof window === "undefined") return;

    // Initialize root history state if empty
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

  // Synchronize Firebase Auth State across browser refreshes with fail-closed role verification
  useEffect(() => {
    if (typeof window === "undefined" || !isFirebaseEnabled()) return;
    const auth = getFirebaseAuth();
    if (!auth) return;

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user && user.email) {
        const email = user.email;
        const role = getRoleFromEmail(email);

        // Unknown role or unmapped email: immediately revoke session
        if (!role) {
          try {
            await signOut(auth);
          } catch {}
          return;
        }

        // If currently in a specific portal, verify role matches that portal
        if (portal === "patient" && role !== "patient") {
          try {
            await signOut(auth);
            setScreenState("login");
          } catch {}
          return;
        }

        if (portal === "provider" && role !== "provider") {
          try {
            await signOut(auth);
            setProviderScreenState("login");
          } catch {}
          return;
        }

        if (portal === "admin" && role !== "admin") {
          try {
            await signOut(auth);
            setAdminScreenState("login");
          } catch {}
          return;
        }

        // Set matching role identifier
        if (role === "patient") {
          setUserIdentifier(email);
        } else if (role === "provider") {
          setProviderIdentifier(email);
        } else if (role === "admin") {
          setAdminIdentifier(email);
        }
      }
    });

    return () => unsubscribe();
  }, [portal]);

  const signOutUser = async () => {
    if (isFirebaseEnabled()) {
      const auth = getFirebaseAuth();
      if (auth) {
        try {
          await signOut(auth);
        } catch {
          // Silent catch on unmount or network disconnect
        }
      }
    }
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
