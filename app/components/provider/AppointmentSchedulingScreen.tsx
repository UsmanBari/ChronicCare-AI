"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import { api, Appointment } from "../../lib/api";
import { Calendar, Clock, CheckCircle2, User, Stethoscope, ArrowLeft, AlertCircle, AlertTriangle, ShieldCheck, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

export const AppointmentSchedulingScreen = () => {
  const {
    setProviderScreen,
    setAppointment,
    demoScenario,
    providerIdentifier,
    providerDisplayName,
    language,
    isLiveMode,
    t,
    isUrdu,
  } = useApp();

  const fallbackProvider = isUrdu ? "ڈاکٹر" : ((language as string) === "roman_ur" ? "Doctor" : "Provider");
  const activeProviderName = isLiveMode
    ? (providerDisplayName || providerIdentifier || fallbackProvider)
    : "Dr. Sana Malik";

  const [activeTab, setActiveTab] = useState<"queue" | "manual">("queue");
  const [liveAppointments, setLiveAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchProviderAppointments = async () => {
    if (!isLiveMode) {
      setLiveAppointments([]);
      return;
    }
    setIsLoading(true);
    try {
      const res = await api.getProviderAppointments();
      setLiveAppointments(res.appointments || []);
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProviderAppointments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAcknowledge = async (id: string) => {
    try {
      await api.acknowledgeAppointment(id);
      setActionMessage("Appointment acknowledged; escalation alert cleared.");
      await fetchProviderAppointments();
    } catch (err: any) {
      setActionMessage(err.message || "Failed to acknowledge");
    }
  };

  const handleMarkAttended = async (id: string) => {
    try {
      await api.markAppointmentAttended(id);
      setActionMessage("Appointment marked as attended.");
      await fetchProviderAppointments();
    } catch (err: any) {
      setActionMessage(err.message || "Failed to mark attended");
    }
  };

  // Mock slot selection state
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
      provider: activeProviderName,
      status: "Confirmed",
      bookedAt: "Just now",
    });

    setIsBooked(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto surface-card rounded-2xl overflow-hidden shadow-lg border border-slate-200"
      dir={isUrdu ? "rtl" : "ltr"}
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

        {/* Tab switcher */}
        <div className="flex justify-center gap-2 mt-4">
          <button
            type="button"
            onClick={() => setActiveTab("queue")}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === "queue"
                ? "bg-teal-600 text-white shadow-xs"
                : "bg-navy-700 text-slate-300 hover:text-white"
            }`}
          >
            {isUrdu ? "ملاقاتوں کی فہرست" : "Appointments Queue"} ({liveAppointments.length})
          </button>
          {!isLiveMode && (
            <button
              type="button"
              onClick={() => setActiveTab("manual")}
              className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === "manual"
                  ? "bg-teal-600 text-white shadow-xs"
                  : "bg-navy-700 text-slate-300 hover:text-white"
              }`}
            >
              {isUrdu ? "مینوئل بکنگ" : "Schedule Follow-up"}
            </button>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {actionMessage && (
          <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-900 text-xs flex items-center justify-between">
            <span>{actionMessage}</span>
            <button type="button" onClick={() => setActionMessage(null)} className="text-teal-700 font-bold ml-2">×</button>
          </div>
        )}

        {activeTab === "queue" ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                {isUrdu ? "طبی نگہداشت کی تقرریاں" : "Triaged Appointments Roster"}
              </span>
              <button
                type="button"
                onClick={fetchProviderAppointments}
                className="text-xs text-teal-700 hover:text-teal-800 font-semibold flex items-center gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                <span>{isUrdu ? "تازہ کریں" : "Refresh"}</span>
              </button>
            </div>

            {liveAppointments.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200 text-slate-500 text-xs">
                {isUrdu ? "فی الوقت کوئی تقرری زیر التوا نہیں ہے۔" : "No appointments in the queue."}
              </div>
            ) : (
              <div className="space-y-3">
                {liveAppointments.map((apt) => {
                  const isUrgent = apt.urgency === "urgent";
                  const isBooked = apt.status === "booked";
                  const isAcknowledged = Boolean(apt.acknowledged_at);
                  const isAttended = apt.status === "attended";
                  const isEscalated = apt.escalation_state === "admin_flag";

                  return (
                    <div
                      key={apt.id}
                      className={`p-4 rounded-2xl border transition-all space-y-3 ${
                        isUrgent
                          ? "bg-red-50/60 border-red-300 ring-1 ring-red-300"
                          : "bg-white border-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                            isUrgent ? "bg-red-600 text-white" : "bg-teal-100 text-teal-900 border border-teal-200"
                          }`}>
                            {apt.urgency === "urgent" ? t.urgencyUrgent : t.urgencyRoutine}
                          </span>
                          <span className="text-xs font-bold text-navy-800">
                            Patient: {(apt as any).patient_label || (apt as any).patient_name || apt.patient_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] px-2 py-0.5 rounded-md font-semibold bg-slate-100 text-slate-700">
                            {apt.status === "offered" ? t.appointmentOffered : apt.status === "booked" ? t.appointmentBooked : apt.status === "cancelled" ? t.appointmentCancelled : t.appointmentAttended}
                          </span>
                          {isEscalated && (
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-rose-600 text-white font-bold animate-pulse">
                              {t.escalationAdminFlag}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-1">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">{t.appointmentSpecialty}</span>
                          <span className="font-semibold text-navy-800">
                            {apt.specialty === "endocrinology" ? t.specialtyEndocrinology : apt.specialty === "cardiology_im" ? t.specialtyCardiology : apt.specialty === "internal_medicine" ? t.specialtyInternalMedicine : t.specialtyGeneral}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">{isUrdu ? "ملاقات کا وقت" : "Slot"}</span>
                          <span className="font-semibold text-navy-800">{apt.slot_date || apt.slot || "Awaiting booking"}</span>
                        </div>
                      </div>

                      <div className="text-xs text-slate-500">
                        <span className="font-semibold text-slate-700">{t.appointmentReason}:</span> {apt.reason || "Routine clinical review"}
                      </div>

                      {/* Action buttons */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
                        {isBooked && !isAcknowledged && (
                          <button
                            type="button"
                            onClick={() => handleAcknowledge(apt.id)}
                            className="min-h-[34px] px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl shadow-2xs flex items-center gap-1.5"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>{t.acknowledgeAppointmentBtn}</span>
                          </button>
                        )}
                        {isAcknowledged && !isAttended && (
                          <button
                            type="button"
                            onClick={() => handleMarkAttended(apt.id)}
                            className="min-h-[34px] px-3.5 py-1.5 bg-navy-800 hover:bg-navy-900 text-white font-bold text-xs rounded-xl shadow-2xs flex items-center gap-1.5"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>{t.markAttendedBtn}</span>
                          </button>
                        )}
                        {isAttended && (
                          <span className="text-xs text-mutedGreen-800 font-bold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Attended
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setProviderScreen("dashboard")}
                className="w-full min-h-[44px] py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all"
              >
                {t.backToDashboard}
              </button>
            </div>
          </div>
        ) : !isBooked ? (
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
                {activeProviderName}
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
                <span className="font-bold text-navy-800">{activeProviderName}</span>
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
