"use client";

import React, { useState } from "react";
import { useApp } from "./context/AppContext";
import { Header } from "./components/Header";
import { DemoFooter } from "./components/DemoFooter";
import { PortalLandingScreen } from "./components/PortalLandingScreen";
import { UnifiedSettingsModal } from "./components/UnifiedSettingsModal";
import { EvaluatorTourModal } from "./components/EvaluatorTourModal";
import { Preloader } from "./components/Preloader";
import { motion, AnimatePresence } from "framer-motion";
import { HelpCircle, X, Sparkles } from "lucide-react";

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

const screenTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.22, ease: "easeOut" as const },
};

export default function App() {
  const { portal, screen, providerScreen, adminScreen, showTour, setShowTour } = useApp();
  const [hasLoaded, setHasLoaded] = useState(false);
  const [dismissTourToast, setDismissTourToast] = useState(false);

  // Compute a unique key for the active screen to drive AnimatePresence
  const activeKey =
    portal === "landing"
      ? "portal-landing"
      : portal === "patient"
      ? `patient-${screen}`
      : portal === "provider"
      ? `provider-${providerScreen}`
      : `admin-${adminScreen}`;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      {/* Session Preloader on First App Load */}
      <AnimatePresence>
        {!hasLoaded && (
          <Preloader onComplete={() => setHasLoaded(true)} />
        )}
      </AnimatePresence>

      {/* Top Header */}
      <Header />

      {/* Evaluator Tour Guide Modal (Self-Guided Presentation Tour - Open via Header or Toast) */}
      <EvaluatorTourModal isOpen={showTour} onClose={() => setShowTour(false)} />

      {/* Unified Settings Modal (Global) */}
      <UnifiedSettingsModal />

      {/* Non-Blocking Floating Evaluator Toast on Landing (Responsive full-width bottom bar on mobile, floating card on desktop) */}
      {hasLoaded && !showTour && !dismissTourToast && portal === "landing" && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 15 }}
          transition={{ duration: 0.35, delay: 0.5 }}
          className="fixed bottom-0 left-0 right-0 md:bottom-14 md:right-6 md:left-auto z-40 w-full md:w-auto md:max-w-sm bg-white/95 backdrop-blur-md border-t md:border border-teal-200/90 rounded-none md:rounded-2xl p-3 md:p-3.5 shadow-2xl md:shadow-xl flex items-center justify-between gap-3"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-xs font-bold text-navy-800 block truncate">Evaluator Guided Tour</span>
              <span className="text-[11px] text-slate-500 block leading-tight truncate">1-min FYP demo walkthrough</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => setShowTour(true)}
              className="min-h-[44px] px-3 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs transition-colors shadow-2xs flex items-center justify-center"
            >
              Start Tour
            </button>
            <button
              type="button"
              onClick={() => setDismissTourToast(true)}
              title="Dismiss"
              className="min-h-[44px] min-w-[44px] p-2 text-slate-400 hover:text-slate-600 rounded-lg transition-colors flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}

      {/* Main Flow Viewport with AnimatePresence Transitions */}
      <main className="flex-1 w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeKey}
            initial={screenTransition.initial}
            animate={screenTransition.animate}
            exit={screenTransition.exit}
            transition={screenTransition.transition}
            className="w-full"
          >
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
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Demo Watermark and Scope Footer */}
      <DemoFooter />
    </div>
  );
}
