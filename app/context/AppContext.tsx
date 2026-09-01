"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { Language, translations, Translations } from "../translations";

export type ScreenType =
  | "login"
  | "connection"
  | "profile"
  | "home"
  | "checkin_entry"
  | "adaptive_interview"
  | "confirmation"
  | "processing"
  | "risk_result"
  | "trends";

export type ConnectionMode = "fhir" | "offline" | null;
export type MissedMedsOption = "yes" | "no" | "prefer_not_to_answer" | null;
export type RiskLevel = "low" | "moderate" | "high";

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

interface AppContextType {
  screen: ScreenType;
  setScreen: (screen: ScreenType) => void;
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
  isUrdu: boolean;
  
  // Auth state (Mocked UI)
  userIdentifier: string;
  setUserIdentifier: (id: string) => void;
  
  // Connection choice state (Mocked)
  connectionMode: ConnectionMode;
  setConnectionMode: (mode: ConnectionMode) => void;
  
  // Health profile state (Mocked)
  profile: HealthProfile;
  setProfile: React.Dispatch<React.SetStateAction<HealthProfile>>;
  
  // Daily check-in data
  checkIn: CheckInData;
  setCheckIn: React.Dispatch<React.SetStateAction<CheckInData>>;
  
  // Reset session
  resetSession: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [screen, setScreen] = useState<ScreenType>("login");
  const [language, setLanguage] = useState<Language>("en");
  const [userIdentifier, setUserIdentifier] = useState<string>("");
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>(null);
  
  const [profile, setProfile] = useState<HealthProfile>({
    conditions: ["Type 2 Diabetes"],
    medications: ["Metformin 500mg (Daily)"],
    age: "58",
  });
  
  const [checkIn, setCheckIn] = useState<CheckInData>({
    note: "",
    thirst: null,
    urination: null,
    missedMeds: null,
    lowConfidence: false,
    submittedAt: null,
  });

  const t = translations[language];
  const isUrdu = language === "ur";

  const resetSession = () => {
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

  return (
    <AppContext.Provider
      value={{
        screen,
        setScreen,
        language,
        setLanguage,
        t,
        isUrdu,
        userIdentifier,
        setUserIdentifier,
        connectionMode,
        setConnectionMode,
        profile,
        setProfile,
        checkIn,
        setCheckIn,
        resetSession,
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
