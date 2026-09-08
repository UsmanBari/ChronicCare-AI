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
      <main className="flex-1 w-full">
        {/* Landing Portal Selection */}
        {portal === "landing" && <PortalLandingScreen />}

        {/* Patient Portal Flow */}
        {portal === "patient" && (
          <div className="w-full">
            {/* Narrow / Auth & Interview Screens */}
            {(screen === "login" ||
              screen === "connection" ||
              screen === "profile" ||
              screen === "checkin_entry" ||
              screen === "adaptive_interview" ||
              screen === "confirmation" ||
              screen === "processing" ||
              screen === "risk_result" ||
              screen === "conflict_detail" ||
              screen === "conflict_review" ||
              screen === "emergency") && (
              <div className="max-w-xl mx-auto px-4 sm:px-6 py-6 md:py-10 flex flex-col items-center justify-center min-h-[calc(100vh-140px)]">
                {screen === "login" && <LoginScreen />}
                {screen === "connection" && <ConnectionScreen />}
                {screen === "profile" && <HealthProfileScreen />}
                {screen === "checkin_entry" && <CheckInEntryScreen />}
                {screen === "adaptive_interview" && <AdaptiveInterviewScreen />}
                {screen === "confirmation" && <ConfirmationScreen />}
                {screen === "processing" && <ProcessingScreen />}
                {screen === "risk_result" && <RiskResultScreen />}
                {screen === "conflict_detail" && <ConflictScreen />}
                {screen === "conflict_review" && <RoutedToReviewScreen />}
                {screen === "emergency" && <EmergencyScreen />}
              </div>
            )}

            {/* Dashboard & Content Rich Patient Screens */}
            {screen === "home" && (
              <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 md:py-8">
                <HomeScreen />
              </div>
            )}
            {screen === "trends" && (
              <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 md:py-8">
                <TrendScreen />
              </div>
            )}
            {screen === "appointments" && (
              <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 md:py-8">
                <PatientAppointmentsScreen />
              </div>
            )}
          </div>
        )}

        {/* Provider Portal Flow */}
        {portal === "provider" && (
          <div className="w-full">
            {providerScreen === "login" && (
              <div className="max-w-md mx-auto px-4 py-10 flex flex-col items-center justify-center min-h-[calc(100vh-140px)]">
                <ProviderLoginScreen />
              </div>
            )}
            {providerScreen === "dashboard" && (
              <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <ProviderDashboardScreen />
              </div>
            )}
            {providerScreen === "review_queue" && (
              <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <ReviewQueueScreen />
              </div>
            )}
            {providerScreen === "reconciliation_alert" && (
              <div className="max-w-5xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <ReconciliationAlertDetail />
              </div>
            )}
            {providerScreen === "patient_detail" && (
              <div className="max-w-5xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <PatientDetailScreen />
              </div>
            )}
            {providerScreen === "schedule_appointment" && (
              <div className="max-w-3xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <AppointmentSchedulingScreen />
              </div>
            )}
          </div>
        )}

        {/* Admin Portal Flow */}
        {portal === "admin" && (
          <div className="w-full">
            {adminScreen === "login" && (
              <div className="max-w-md mx-auto px-4 py-10 flex flex-col items-center justify-center min-h-[calc(100vh-140px)]">
                <AdminLoginScreen />
              </div>
            )}
            {adminScreen === "dashboard" && (
              <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">
                <AdminDashboardScreen />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Demo Watermark and Scope Footer */}
      <DemoFooter />
    </div>
  );
}
