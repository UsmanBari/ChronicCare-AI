"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  Sparkles,
  SlidersHorizontal,
  ClipboardList,
  ShieldCheck,
  ArrowRight,
  X,
  Activity,
  HeartPulse,
} from "lucide-react";
import { motion, AnimatePresence, Variants } from "framer-motion";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.25 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

const modalVariants: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring",
      stiffness: 280,
      damping: 24,
      staggerChildren: 0.08,
      delayChildren: 0.08,
    },
  },
  exit: {
    opacity: 0,
    y: 16,
    scale: 0.96,
    transition: { duration: 0.2, ease: "easeIn" },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" } },
};

export const EvaluatorTourModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { isUrdu } = useApp();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="evaluator-modal-backdrop"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-navy-950/75 backdrop-blur-sm"
        >
          <motion.div
            key="evaluator-modal-card"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="w-full max-w-2xl bg-white rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden relative"
            style={{
              background:
                "radial-gradient(circle at 100% 0%, rgba(11, 110, 112, 0.06), transparent 50%), #FFFFFF",
            }}
            dir={isUrdu ? "rtl" : "ltr"}
          >
            {/* Modal Header */}
            <motion.div
              variants={itemVariants}
              className="bg-gradient-to-r from-navy-900 via-navy-800 to-teal-900 p-6 sm:p-7 text-white relative overflow-hidden"
            >
              {/* Living Faint Activity Watermark */}
              <motion.div
                animate={{ scale: [1, 1.08, 1], opacity: [0.08, 0.14, 0.08] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -bottom-6 -right-6 text-teal-300 pointer-events-none"
              >
                <Activity className="w-40 h-40" />
              </motion.div>

              <button
                type="button"
                onClick={onClose}
                id="close-tour-modal-btn"
                aria-label="Close"
                className="absolute top-5 right-5 p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors z-10"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-400/20 text-teal-300 text-xs font-bold uppercase tracking-wider mb-2.5 border border-teal-400/30">
                <Sparkles className="w-3.5 h-3.5 text-teal-300" />
                <span>{isUrdu ? "رہنما برائے مبصرین" : "SELF-GUIDED EVALUATOR TOUR"}</span>
              </div>

              <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {isUrdu ? "کرونک کیئر اے آئی میں خوش آمدید" : "Welcome to ChronicCare AI"}
              </h2>

              {/* Motto Line */}
              <p className="font-serif italic text-teal-300 text-base sm:text-lg mt-1.5 leading-snug">
                {isUrdu
                  ? "«دائمی نگہداشت کا تسلسل، ہر چیک اپ کے درمیان۔»"
                  : '"Continuity of care, between every visit."'}
              </p>

              <p className="text-xs text-slate-300 mt-2 font-sans opacity-90">
                {isUrdu
                  ? "فاسٹ یونیورسٹی بی ایس فائنل ایئر پروجیکٹ پروپوزل ڈیفنس پروٹو ٹائپ"
                  : "Interactive UI Prototype for FAST-NUCES FYP Proposal Defense"}
              </p>
            </motion.div>

            {/* Modal Body: 3-Column Compact Stepper */}
            <div className="p-6 sm:p-7 space-y-6">
              
              {/* Stepper with connecting line */}
              <motion.div variants={itemVariants} className="relative">
                {/* Connecting Track Line (Desktop only) */}
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
                  className="hidden md:block absolute top-6 left-12 right-12 h-0.5 bg-gradient-to-r from-teal-500 via-teal-400 to-teal-600 origin-left z-0"
                />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5 relative z-10">
                  
                  {/* Step 1 */}
                  <motion.div
                    whileHover={{ y: -3 }}
                    transition={{ type: "spring", stiffness: 350, damping: 20 }}
                    className="p-4 sm:p-4.5 rounded-2xl bg-slate-50/90 border border-slate-200/80 shadow-xs flex flex-col justify-between space-y-3 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-teal-700 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
                        1
                      </div>
                      <div className="font-heading font-bold text-sm text-navy-800 flex items-center gap-1.5">
                        <SlidersHorizontal className="w-4 h-4 text-teal-700" />
                        <span>Test 3 Scenarios</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Toggle Normal, Discrepancy Conflict, or Urgent triage in Presenter Controls.
                    </p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-bold text-slate-700">
                        Normal
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-amber-50 border border-amber-200 text-[10px] font-bold text-amber-900">
                        Conflict
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-red-50 border border-red-200 text-[10px] font-bold text-red-800">
                        Emergency
                      </span>
                    </div>
                  </motion.div>

                  {/* Step 2 */}
                  <motion.div
                    whileHover={{ y: -3 }}
                    transition={{ type: "spring", stiffness: 350, damping: 20 }}
                    className="p-4 sm:p-4.5 rounded-2xl bg-slate-50/90 border border-slate-200/80 shadow-xs flex flex-col justify-between space-y-3 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-teal-700 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
                        2
                      </div>
                      <div className="font-heading font-bold text-sm text-navy-800 flex items-center gap-1.5">
                        <ClipboardList className="w-4 h-4 text-teal-700" />
                        <span>Review Alerts</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Switch to Provider Portal (Dr. Sana) to triage glucose conflicts & alerts.
                    </p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-bold text-slate-700">
                        Review Queue
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-teal-50 border border-teal-200 text-[10px] font-bold text-teal-800">
                        Resolution
                      </span>
                    </div>
                  </motion.div>

                  {/* Step 3 */}
                  <motion.div
                    whileHover={{ y: -3 }}
                    transition={{ type: "spring", stiffness: 350, damping: 20 }}
                    className="p-4 sm:p-4.5 rounded-2xl bg-slate-50/90 border border-slate-200/80 shadow-xs flex flex-col justify-between space-y-3 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-teal-700 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
                        3
                      </div>
                      <div className="font-heading font-bold text-sm text-navy-800 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-teal-700" />
                        <span>Cross-Portal Sync</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Follow-up bookings and alert counters sync across Patient & Admin.
                    </p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-bold text-slate-700">
                        Appointments
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-mutedGreen-50 border border-mutedGreen-200 text-[10px] font-bold text-mutedGreen-800">
                        Live FHIR
                      </span>
                    </div>
                  </motion.div>
                </div>
              </motion.div>

              {/* Modal Footer with Spring Interaction Button */}
              <motion.div
                variants={itemVariants}
                className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-200/80"
              >
                <span className="text-xs text-slate-500 text-center sm:text-left">
                  {isUrdu
                    ? "آپ اس رہنما کو ہیڈر کے بٹن سے کسی بھی وقت دوبارہ کھول سکتے ہیں۔"
                    : "Reopen this guide anytime via the Guide button in the top navigation."}
                </span>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  type="button"
                  onClick={onClose}
                  id="start-evaluator-tour-btn"
                  className="w-full sm:w-auto min-h-[48px] px-6 py-3 bg-teal-700 hover:bg-teal-800 text-white font-bold text-sm rounded-xl shadow-lg shadow-teal-800/20 transition-colors flex items-center justify-center gap-2 shrink-0"
                >
                  <span>{isUrdu ? "رہنمائی شروع کریں" : "Start Interactive Walkthrough"}</span>
                  <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
                </motion.button>
              </motion.div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
