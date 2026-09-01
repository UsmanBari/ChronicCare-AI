"use client";

import React from "react";
import { useApp } from "./context/AppContext";
import { Header } from "./components/Header";
import { DemoFooter } from "./components/DemoFooter";
import { PortalLandingScreen } from "./components/PortalLandingScreen";
import { UnifiedSettingsModal } from "./components/UnifiedSettingsModal";
import { EvaluatorTourModal } from "./components/EvaluatorTourModal";

// Patient Portal Components
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
import { PatientAppointmentsScreen } from "./components/PatientAppointmentsScreen";

// Provider Portal Components
import { ProviderLoginScreen } from "./components/provider/ProviderLoginScreen";
import { ProviderDashboardScreen } from "./components/provider/ProviderDashboardScreen";
import { ReviewQueueScreen } from "./components/provider/ReviewQueueScreen";
import { ReconciliationAlertDetail } from "./components/provider/ReconciliationAlertDetail";
import { PatientDetailScreen } from "./components/provider/PatientDetailScreen";
import { AppointmentSchedulingScreen } from "./components/provider/AppointmentSchedulingScreen";

// Admin Portal Components
import { AdminLoginScreen } from "./components/admin/AdminLoginScreen";
import { AdminDashboardScreen } from "./components/admin/AdminDashboardScreen";

export default function App() {
  const { portal, screen, providerScreen, adminScreen, showTour, setShowTour } = useApp();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      {/* Top Header */}
      <Header />

      {/* Evaluator Tour Guide Modal (Self-Guided Presentation Tour) */}
      <EvaluatorTourModal isOpen={showTour} onClose={() => setShowTour(false)} />

      {/* Unified Settings Modal (Global) */}
      <UnifiedSettingsModal />

      {/* Main Flow Viewport */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-8">
        {/* Landing Portal Selection */}
        {portal === "landing" && <PortalLandingScreen />}

        {/* Patient Portal Flow */}
        {portal === "patient" && (
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
            {screen === "appointments" && <PatientAppointmentsScreen />}
          </div>
        )}

        {/* Provider Portal Flow */}
        {portal === "provider" && (
          <div className="w-full">
            {providerScreen === "login" && <ProviderLoginScreen />}
            {providerScreen === "dashboard" && <ProviderDashboardScreen />}
            {providerScreen === "review_queue" && <ReviewQueueScreen />}
            {providerScreen === "reconciliation_alert" && <ReconciliationAlertDetail />}
            {providerScreen === "patient_detail" && <PatientDetailScreen />}
            {providerScreen === "schedule_appointment" && <AppointmentSchedulingScreen />}
          </div>
        )}

        {/* Admin Portal Flow */}
        {portal === "admin" && (
          <div className="w-full">
            {adminScreen === "login" && <AdminLoginScreen />}
            {adminScreen === "dashboard" && <AdminDashboardScreen />}
          </div>
        )}
      </main>

      {/* Demo Watermark and Scope Footer */}
      <DemoFooter />
    </div>
  );
}
