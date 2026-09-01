"use client";

import React from "react";
import { useApp } from "./context/AppContext";
import { Header } from "./components/Header";
import { DemoFooter } from "./components/DemoFooter";
import { LoginScreen } from "./components/LoginScreen";
import { ConnectionScreen } from "./components/ConnectionScreen";
import { HealthProfileScreen } from "./components/HealthProfileScreen";
import { HomeScreen } from "./components/HomeScreen";
import { CheckInEntryScreen } from "./components/CheckInEntryScreen";
import { AdaptiveInterviewScreen } from "./components/AdaptiveInterviewScreen";
import { ConfirmationScreen } from "./components/ConfirmationScreen";
import { ProcessingScreen } from "./components/ProcessingScreen";
import { RiskResultScreen } from "./components/RiskResultScreen";
import { TrendScreen } from "./components/TrendScreen";
import { ConflictScreen } from "./components/ConflictScreen";
import { RoutedToReviewScreen } from "./components/RoutedToReviewScreen";
import { EmergencyScreen } from "./components/EmergencyScreen";

export default function App() {
  const { screen } = useApp();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      {/* Top Header */}
      <Header />

      {/* Main Flow Viewport */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-xl">
          {screen === "login" && <LoginScreen />}
          {screen === "connection" && <ConnectionScreen />}
          {screen === "profile" && <HealthProfileScreen />}
          {screen === "home" && <HomeScreen />}
          {screen === "checkin_entry" && <CheckInEntryScreen />}
          {screen === "adaptive_interview" && <AdaptiveInterviewScreen />}
          {screen === "confirmation" && <ConfirmationScreen />}
          {screen === "processing" && <ProcessingScreen />}
          {screen === "risk_result" && <RiskResultScreen />}
          {screen === "trends" && <TrendScreen />}
          {screen === "conflict_detail" && <ConflictScreen />}
          {screen === "conflict_review" && <RoutedToReviewScreen />}
          {screen === "emergency" && <EmergencyScreen />}
        </div>
      </main>

      {/* Demo Watermark and Scope Footer */}
      <DemoFooter />
    </div>
  );
}
