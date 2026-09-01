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
  Stethoscope,
  Info,
} from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const EvaluatorTourModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { setPortal, setScreen } = useApp();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-900/70 backdrop-blur-xs animate-fadeIn">
      <div className="w-full max-w-lg bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden animate-slideUp">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-navy-900 via-navy-800 to-teal-900 p-6 text-white relative">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-400/20 text-teal-300 text-[10px] font-bold uppercase tracking-wider mb-2 border border-teal-400/30">
            <Sparkles className="w-3 h-3 text-teal-300" />
            <span>Self-Guided Evaluator Tour</span>
          </div>
          <h2 className="font-heading text-2xl font-bold text-white">
            Welcome to ChronicCare AI
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Interactive UI Prototype for FAST-NUCES FYP Proposal Defense
          </p>
        </div>

        {/* Modal Body: 3 Step Guide */}
        <div className="p-6 space-y-4 text-xs text-slate-700 max-h-[70vh] overflow-y-auto">
          <div className="p-3.5 rounded-2xl bg-teal-50/70 border border-teal-200 text-teal-950 flex items-start gap-3">
            <Info className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-xs block text-navy-800">
                Interactive Interaction Layer
              </span>
              <p className="text-[11px] leading-relaxed text-slate-600">
                Everything you click is fully responsive and interactive. Computational risk inference, FHIR connections, and calendar bookings are mocked for demonstration.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-1">
            {/* Step 1 */}
            <div className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-400 transition-colors flex items-start gap-3 bg-slate-50/50">
              <div className="w-7 h-7 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0 font-bold text-xs">
                1
              </div>
              <div className="space-y-0.5">
                <span className="font-bold text-navy-800 block text-xs flex items-center gap-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-teal-700" />
                  <span>Explore Presenter Controls (Patient Portal)</span>
                </span>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Start on the <strong>Patient Portal</strong>. On the Home screen, look for the dashed <em>Presenter Controls</em> box to test <strong>Scenario A (Normal)</strong>, <strong>Scenario B (Conflict)</strong>, and <strong>Scenario C (Emergency)</strong>.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-400 transition-colors flex items-start gap-3 bg-slate-50/50">
              <div className="w-7 h-7 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0 font-bold text-xs">
                2
              </div>
              <div className="space-y-0.5">
                <span className="font-bold text-navy-800 block text-xs flex items-center gap-1.5">
                  <ClipboardList className="w-3.5 h-3.5 text-teal-700" />
                  <span>Clinical Review Queue (Provider Portal)</span>
                </span>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Switch to the <strong>Provider Portal</strong> (Dr. Sana Malik) using the top header to inspect the live discrepancy alert (180 vs 140 mg/dL), resolve cases, or book follow-up appointments.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-400 transition-colors flex items-start gap-3 bg-slate-50/50">
              <div className="w-7 h-7 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0 font-bold text-xs">
                3
              </div>
              <div className="space-y-0.5">
                <span className="font-bold text-navy-800 block text-xs flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
                  <span>Cross-Portal Synchronization & Admin</span>
                </span>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Appointments booked by Dr. Sana Malik immediately synchronize to Ali Khan&apos;s <em>&quot;My Appointments&quot;</em> view, while Active Alerts mirror across Provider and Admin dashboards.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-5 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-[10px] text-slate-500 text-center sm:text-left">
            You can reopen this guide anytime from the header.
          </span>
          <button
            type="button"
            onClick={onClose}
            id="start-evaluator-tour-btn"
            className="w-full sm:w-auto py-2.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.98] text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <span>Start Interactive Walkthrough</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
