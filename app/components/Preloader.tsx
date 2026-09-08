"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, CheckCircle2, Sparkles } from "lucide-react";
import { useApp } from "../context/AppContext";

export const Preloader = ({ onComplete }: { onComplete: () => void }) => {
  const { isUrdu } = useApp();
  const [progress, setProgress] = useState(0);
  const [showWelcome, setShowWelcome] = useState(false);

  useEffect(() => {
    const duration = 1600;
    const start = Date.now();
    let frameId: number;

    const tick = () => {
      const elapsed = Date.now() - start;
      const pct = Math.min(100, Math.round((elapsed / duration) * 100));
      setProgress(pct);

      if (pct < 100) {
        frameId = requestAnimationFrame(tick);
      } else {
        // Trigger the brief Welcome beat (Hold for 2.3s)
        setShowWelcome(true);
        setTimeout(() => {
          onComplete();
        }, 2300);
      }
    };

    frameId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [onComplete]);

  // Phase-dependent supporting status copy
  const getStatusMessage = () => {
    if (isUrdu) {
      if (progress < 30) return "کلینیکل انجن شروع ہو رہا ہے…";
      if (progress < 65) return "مریض کا ڈیٹا اور ٹیلی میٹری لوڈ ہو رہی ہے…";
      if (progress < 90) return "ہسپتال کے FHIR سسٹم سے رابطہ قائم ہو رہا ہے…";
      return "سسٹم تیار ہے۔";
    }
    if (progress < 30) return "Initializing clinical engine…";
    if (progress < 65) return "Loading patient telemetry & profiles…";
    if (progress < 90) return "Establishing HL7® FHIR® EHR connection…";
    return "Clinical engine ready.";
  };

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1.0, ease: "easeInOut" }}
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#0A0F1C] select-none overflow-hidden px-4 text-center"
    >
      {/* Part B: Full-screen Animated Heartbeat / EKG Waveform in Background */}
      <svg
        className="absolute inset-0 w-full h-full opacity-20 pointer-events-none"
        viewBox="0 0 800 200"
        preserveAspectRatio="none"
      >
        <motion.path
          d="M0,100 L150,100 L170,100 L185,35 L200,165 L215,100 L230,100 L400,100 L420,100 L435,50 L450,150 L465,100 L480,100 L800,100"
          stroke="#17A2A5"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0.8 }}
          animate={{ pathLength: 1, opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
        />
      </svg>

      {/* Ambient Lighting Glow Behind Center Stack */}
      <div className="absolute w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -translate-y-10" />

      <AnimatePresence mode="wait">
        {!showWelcome ? (
          /* Part A: High-Impact Hero Loading Sequence */
          <motion.div
            key="loading-content"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, y: -15, scale: 0.98 }}
            transition={{ duration: 0.3 }}
            className="relative z-10 flex flex-col items-center justify-center w-full max-w-2xl mx-auto"
          >
            {/* Large Glowing Logo Mark (96-120px scale) */}
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              className="w-24 h-24 sm:w-28 sm:h-28 rounded-3xl bg-[#111A2E] border-2 border-teal-500/40 flex items-center justify-center mb-6 shadow-2xl shadow-teal-500/20"
            >
              <Activity className="w-12 h-12 sm:w-14 sm:h-14 text-teal-400 drop-shadow-[0_0_12px_rgba(23,162,165,0.6)]" />
            </motion.div>

            {/* Large Wordmark */}
            <h1 className="font-heading text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-white mb-2">
              ChronicCare AI
            </h1>

            {/* Letter-Spaced Tagline */}
            <span className="text-[11px] sm:text-xs uppercase tracking-[0.28em] text-teal-400/80 font-bold mb-8 sm:mb-10">
              {isUrdu ? "دائمی نگہداشت کا ذہین کلینیکل انجن" : "Clinical Continuity Engine"}
            </span>

            {/* Massive Hero Percentage Counter (80-110px scale) */}
            <div className="font-mono text-7xl sm:text-8xl md:text-9xl font-extrabold text-white tracking-tight tabular-nums leading-none mb-6 drop-shadow-xl">
              {progress}
              <span className="text-3xl sm:text-4xl text-teal-400 font-sans ml-1 font-bold">%</span>
            </div>

            {/* Glowing Wide Progress Bar */}
            <div className="w-[85%] sm:w-[70%] max-w-xl h-2 sm:h-2.5 rounded-full bg-[#141E33] overflow-hidden border border-slate-800 shadow-inner mb-4">
              <motion.div
                className="h-full bg-gradient-to-r from-teal-500 via-teal-400 to-teal-300 rounded-full"
                style={{
                  width: `${progress}%`,
                  boxShadow: "0 0 20px rgba(23, 162, 165, 0.75)",
                }}
              />
            </div>

            {/* Dynamic Milestone Supporting Message */}
            <p className="text-xs sm:text-sm font-medium text-slate-400 tracking-wide mt-1 h-5 animate-fadeIn">
              {getStatusMessage()}
            </p>
          </motion.div>
        ) : (
          /* Part C: Welcome Transitional Beat */
          <motion.div
            key="welcome-content"
            initial={{ opacity: 0, scale: 0.92, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ duration: 0.99, ease: "easeOut" }}
            className="relative z-10 flex flex-col items-center justify-center text-center space-y-4 max-w-xl mx-auto"
          >
            <div className="w-16 h-16 rounded-2xl bg-teal-500/20 border border-teal-400/50 flex items-center justify-center text-teal-300 mb-2 shadow-xl shadow-teal-500/30">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <h2 className="font-heading text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight">
              {isUrdu ? "خوش آمدید" : "Welcome."}
            </h2>

            <p className="font-serif italic text-teal-300 text-lg sm:text-2xl leading-relaxed max-w-md">
              {isUrdu
                ? "«دائمی نگہداشت کا تسلسل، ہر چیک اپ کے درمیان۔»"
                : '"Continuity of care, between every visit."'}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
