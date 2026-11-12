"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { api, Appointment } from "../lib/api";
import { Calendar, Clock, Stethoscope, ArrowLeft, CheckCircle2, AlertCircle, ShieldCheck, XCircle } from "lucide-react";

export const PatientAppointmentsScreen = () => {
  const { setScreen, appointment, t, isUrdu, isLiveMode } = useApp();
  const [liveAppointments, setLiveAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedSlots, setSelectedSlots] = useState<Record<string, string>>({});

  const fetchAppointments = async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const res = await api.getMyAppointments();
      setLiveAppointments(res.appointments || []);
    } catch {
      // Offline fallback: keep empty liveAppointments, display mock appointment
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const handleBook = async (aptId: string) => {
    setActionError(null);
    const chosenSlot = selectedSlots[aptId] || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16).replace("T", " ");
    try {
      await api.bookAppointment(aptId, chosenSlot);
      await fetchAppointments();
    } catch (err: any) {
      setActionError(err.message || "Failed to book appointment");
    }
  };

  const handleCancel = async (aptId: string) => {
    setActionError(null);
    try {
      await api.cancelAppointment(aptId);
      await fetchAppointments();
    } catch (err: any) {
      setActionError(err.message || "Failed to cancel appointment");
    }
  };

  const hasLiveAppointments = liveAppointments.length > 0;

  return (
    <div className="w-full max-w-xl mx-auto surface-card rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-navy-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-teal-700/80 border border-teal-400/30 flex items-center justify-center mx-auto mb-2.5 shadow-md">
          <Calendar className="w-7 h-7 text-teal-300" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold mb-1">
          {t.myAppointmentsTitle}
        </h1>
        <p className="text-sm text-slate-300">
          {isUrdu ? "آپ کی طے شدہ طبی ملاقاتوں کی تفصیلات" : "Overview of your scheduled clinical follow-ups."}
        </p>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {actionError && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
        )}

        {hasLiveAppointments ? (
          <div className="space-y-4" data-testid="live-appointments-list">
            {liveAppointments.map((apt) => {
              const isOffered = apt.status === "offered";
              const isBooked = apt.status === "booked";
              const isAcknowledged = Boolean(apt.acknowledged_at);
              const isAttended = apt.status === "attended";
              const isCancelled = apt.status === "cancelled";
              const isUrgent = apt.urgency === "urgent";

              return (
                <div
                  key={apt.id}
                  data-testid={`appointment-card-${apt.id}`}
                  className={`p-5 rounded-2xl border-2 space-y-3.5 animate-fadeIn ${
                    isUrgent
                      ? "bg-red-50/70 border-red-300"
                      : isOffered
                      ? "bg-amber-50/70 border-amber-300"
                      : "bg-teal-50/80 border-teal-300/80"
                  }`}
                >
                  <div className="flex items-center justify-between border-b pb-3 border-slate-200/80">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isUrgent ? "bg-red-600 animate-pulse" : "bg-teal-700"}`} />
                      <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
                        {apt.status === "offered" ? t.appointmentOffered : apt.status === "booked" ? t.appointmentBooked : apt.status === "cancelled" ? t.appointmentCancelled : t.appointmentAttended}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                        isUrgent ? "bg-red-100 text-red-900 border border-red-300" : "bg-teal-100 text-teal-900 border border-teal-200"
                      }`}>
                        {apt.urgency === "urgent" ? t.urgencyUrgent : t.urgencyRoutine}
                      </span>
                      {apt.escalation_state === "admin_flag" && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-600 text-white font-bold animate-pulse">
                          {t.escalationAdminFlag}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2.5 text-sm">
                    <div className="flex items-start gap-3">
                      <Stethoscope className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-[11px] uppercase font-bold text-slate-500 block">
                          {t.appointmentSpecialty}
                        </span>
                        <span className="font-bold text-navy-800 text-sm">
                          {apt.specialty === "endocrinology" ? t.specialtyEndocrinology : apt.specialty === "cardiology_im" ? t.specialtyCardiology : apt.specialty === "internal_medicine" ? t.specialtyInternalMedicine : t.specialtyGeneral}
                        </span>
                        {apt.provider_id && (
                          <span className="text-xs text-slate-500 block font-mono">
                            {apt.provider_id}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <Clock className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-[11px] uppercase font-bold text-slate-500 block">
                          {isUrdu ? "وقت اور تاریخ" : "Scheduled Time / Slot"}
                        </span>
                        <span className="font-bold text-navy-800 text-sm">
                          {apt.slot_date || apt.slot || (isOffered ? t.bookingWindowNotice : "Pending")}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-[11px] uppercase font-bold text-slate-500 block">
                          {t.appointmentReason}
                        </span>
                        <span className="font-medium text-slate-700 text-xs">
                          {apt.reason || (isUrgent ? "Urgent clinical follow-up" : "Routine clinical check-in")}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions based on state */}
                  {isOffered && (
                    <div className="pt-2 border-t border-slate-200/80 space-y-2">
                      <label className="text-xs font-bold text-navy-800 block">
                        {t.selectSlotLabel}
                      </label>
                      <input
                        type="datetime-local"
                        aria-label="Appointment Slot"
                        value={selectedSlots[apt.id] || ""}
                        onChange={(e) => setSelectedSlots({ ...selectedSlots, [apt.id]: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white text-navy-800 focus:ring-2 focus:ring-teal-600"
                      />
                      <button
                        type="button"
                        onClick={() => handleBook(apt.id)}
                        className="w-full min-h-[42px] py-2.5 px-4 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>{t.bookAppointmentBtn}</span>
                      </button>
                    </div>
                  )}

                  {isBooked && (
                    <div className="pt-2 border-t border-slate-200/80 flex items-center justify-end">
                      <button
                        type="button"
                        onClick={() => handleCancel(apt.id)}
                        className="min-h-[36px] py-1.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-all flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5 text-slate-500" />
                        <span>{t.cancelAppointmentBtn}</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : !appointment.isBooked ? (
          /* Empty State */
          <div className="p-8 sm:p-10 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3.5">
            <div className="w-14 h-14 rounded-2xl bg-slate-200/80 text-slate-400 flex items-center justify-center mx-auto">
              <Calendar className="w-7 h-7" />
            </div>
            <h2 className="font-heading text-lg font-bold text-navy-800">
              {t.noAppointmentsTitle}
            </h2>
            <p className="text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
              {t.noAppointmentsDesc}
            </p>
          </div>
        ) : (
          /* Booked Appointment Card (Mock) */
          <div className="p-6 rounded-2xl bg-teal-50/80 border-2 border-teal-300/80 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-teal-200/80 pb-3.5">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-mutedGreen-800 animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-wider text-teal-900">
                  {appointment.status}
                </span>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-mutedGreen-100 text-mutedGreen-800 font-bold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> FHIR Synchronized
              </span>
            </div>

            <div className="space-y-3.5 text-sm">
              <div className="flex items-start gap-3.5">
                <Stethoscope className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs uppercase font-bold text-slate-500 block">
                    {t.appointmentWith}
                  </span>
                  <span className="font-bold text-navy-800 text-base">
                    {appointment.provider}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <Clock className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs uppercase font-bold text-slate-500 block">
                    {isUrdu ? "وقت اور تاریخ" : "Scheduled Time"}
                  </span>
                  <span className="font-bold text-navy-800 text-base">
                    {appointment.slot}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <CheckCircle2 className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs uppercase font-bold text-slate-500 block">
                    {t.appointmentReason}
                  </span>
                  <span className="font-medium text-slate-700">
                    {appointment.reason}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Back to Home Button */}
        <button
          type="button"
          onClick={() => setScreen("home")}
          id="appointments-back-to-home-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          <span>{t.back}</span>
        </button>
      </div>
    </div>
  );
};
