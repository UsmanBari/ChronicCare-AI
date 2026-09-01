"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { Language, translations, Translations } from "../translations";

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
export type DemoScenario = "normal" | "conflict" | "emergency";

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
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [portal, setPortal] = useState<PortalType>("landing");
  const [screen, setScreen] = useState<PatientScreenType>("home");
  const [providerScreen, setProviderScreen] = useState<ProviderScreenType>("dashboard");
  const [adminScreen, setAdminScreen] = useState<AdminScreenType>("dashboard");
  const [showSettings, setShowSettings] = useState<boolean>(false);
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
    medications: ["Metformin 500mg (Daily)"],
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
    setScreen("home");
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
    setDemoScenario("normal");
    setScreen("home");
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
