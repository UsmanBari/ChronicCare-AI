"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { Calendar, Clock, CheckCircle2, User, Stethoscope, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";

export const AppointmentSchedulingScreen = () => {
  const {
    setProviderScreen,
    setAppointment,
    demoScenario,
    t,
    isUrdu,
  } = useApp();

  const slots = [
    "Mon, Sep 7 • 9:00 AM",
    "Mon, Sep 7 • 2:00 PM",
    "Tue, Sep 8 • 10:30 AM",
    "Wed, Sep 9 • 3:15 PM",
    "Thu, Sep 10 • 11:00 AM",
  ];

  const [selectedSlot, setSelectedSlot] = useState(slots[0]);
  const [isBooked, setIsBooked] = useState(false);

  const handleConfirm = () => {
    const reasonText =
      demoScenario === "conflict"
        ? "Follow-up: reconciliation review (glucose discrepancy)"
        : demoScenario === "emergency"
        ? "Follow-up: urgent case review"
        : "Routine chronic care follow-up";

    setAppointment({
      isBooked: true,
      slot: selectedSlot,
      reason: reasonText,
      provider: "Dr. Sana Malik",
      status: "Confirmed",
      bookedAt: "Just now",
    });

    setIsBooked(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-lg mx-auto surface-card rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="w-12 h-12 rounded-xl bg-teal-700/80 border border-teal-400/30 flex items-center justify-center mx-auto mb-2 shadow-sm">
          <Calendar className="w-6 h-6 text-teal-300" />
        </div>
        <h1 className="font-heading text-xl md:text-2xl font-bold tracking-tight text-white mb-1">
          {t.scheduleTitle}
        </h1>
        <p className="text-xs text-slate-300 font-medium">
          {t.scheduleSubtitle}
        </p>
      </div>

      <div className="p-6 space-y-6">
        {!isBooked ? (
          <div className="space-y-5">
            {/* Patient Context Tag */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-teal-100 flex items-center justify-center text-teal-800 font-bold text-xs">
                  AK
                </div>
                <div>
                  <span className="font-bold text-navy-800 block">Ali Khan (58y M)</span>
                  <span className="text-[11px] text-slate-500">MRN-78429 • Type 2 Diabetes</span>
                </div>
              </div>
              <span className="text-[10px] px-2.5 py-1 rounded-md bg-teal-100 text-teal-900 font-bold">
                Dr. Sana Malik
              </span>
            </div>

            {/* Slot Selection */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-teal-700" />
                <span>{t.selectSlotLabel}</span>
              </label>

              <div className="space-y-2">
                {slots.map((slot, index) => (
                  <label
                    key={index}
                    onClick={() => setSelectedSlot(slot)}
                    className={`min-h-[48px] p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all text-xs font-medium ${
                      selectedSlot === slot
                        ? "border-teal-700 bg-teal-50/70 text-teal-950 ring-1 ring-teal-700 font-bold shadow-xs"
                        : "border-slate-200 hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="appointment-slot"
                        checked={selectedSlot === slot}
                        onChange={() => setSelectedSlot(slot)}
                        className="w-4 h-4 text-teal-700 focus:ring-teal-700"
                      />
                      <span>{slot}</span>
                    </div>
                    <span className="text-[10px] text-teal-700 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-100">Available</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => setProviderScreen("review_queue")}
                id="schedule-cancel-btn"
                className="min-h-[48px] px-5 py-3 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl hover:bg-slate-100 active:scale-[0.99] transition-all"
              >
                {t.back}
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                id="schedule-confirm-btn"
                className="min-h-[48px] flex-1 py-3 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{t.confirmBookingBtn}</span>
              </button>
            </div>
          </div>
        ) : (
          /* Confirmation State */
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-5 text-center py-2"
          >
            <div className="w-14 h-14 rounded-2xl bg-mutedGreen-100 border border-mutedGreen-200 flex items-center justify-center mx-auto text-mutedGreen-800">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <div>
              <h2 className="font-heading text-xl font-bold text-navy-800">
                {t.bookingSuccessTitle}
              </h2>
              <p className="text-xs text-mutedGreen-800 font-semibold mt-1">
                {t.bookingSuccessDesc}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-left space-y-2.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Patient:</span>
                <span className="font-bold text-navy-800">Ali Khan</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Consultation Slot:</span>
                <span className="font-bold text-navy-800">{selectedSlot}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Provider:</span>
                <span className="font-bold text-navy-800">Dr. Sana Malik</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-slate-200">
                <span className="text-slate-500">Cross-Portal Sync:</span>
                <span className="font-bold text-mutedGreen-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Patient Portal Updated
                </span>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setProviderScreen("dashboard")}
                id="booking-return-dashboard-btn"
                className="min-h-[48px] w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-xs rounded-xl shadow-sm transition-all"
              >
                {t.backToDashboard}
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

