"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { Calendar, Clock, Stethoscope, ArrowLeft, CheckCircle2, AlertCircle } from "lucide-react";

export const PatientAppointmentsScreen = () => {
  const { setScreen, appointment, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn space-y-0">
      {/* Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="w-12 h-12 rounded-xl bg-teal-700/80 border border-teal-400/30 flex items-center justify-center mx-auto mb-2 shadow-md">
          <Calendar className="w-6 h-6 text-teal-300" />
        </div>
        <h1 className="font-heading text-2xl font-bold mb-1">
          {t.myAppointmentsTitle}
        </h1>
        <p className="text-xs text-slate-300">
          {isUrdu ? "آپ کی طے شدہ طبی ملاقاتوں کی تفصیلات" : "Overview of your scheduled clinical follow-ups."}
        </p>
      </div>

      <div className="p-6 space-y-6">
        {!appointment.isBooked ? (
          /* Empty State */
          <div className="p-8 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-200 text-slate-400 flex items-center justify-center mx-auto">
              <Calendar className="w-6 h-6" />
            </div>
            <h2 className="font-heading text-base font-bold text-navy-800">
              {t.noAppointmentsTitle}
            </h2>
            <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
              {t.noAppointmentsDesc}
            </p>
          </div>
        ) : (
          /* Booked Appointment Card */
          <div className="p-5 rounded-2xl bg-teal-50/70 border border-teal-200 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-teal-200/80 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-mutedGreen-800 animate-ping" />
                <span className="text-xs font-bold uppercase tracking-wider text-teal-900">
                  {appointment.status}
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-mutedGreen-100 text-mutedGreen-800 font-bold">
                ✓ Synced
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-3">
                <Stethoscope className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">
                    {t.appointmentWith}
                  </span>
                  <span className="font-bold text-navy-800 text-sm">
                    {appointment.provider}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Clock className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">
                    {isUrdu ? "وقت اور تاریخ" : "Scheduled Time"}
                  </span>
                  <span className="font-bold text-navy-800 text-sm">
                    {appointment.slot}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">
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
          className="w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          <span>{t.back}</span>
        </button>
      </div>
    </div>
  );
};
