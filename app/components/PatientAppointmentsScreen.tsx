"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { Calendar, Clock, Stethoscope, ArrowLeft, CheckCircle2, AlertCircle, ShieldCheck } from "lucide-react";

export const PatientAppointmentsScreen = () => {
  const { setScreen, appointment, t, isUrdu } = useApp();

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
        {!appointment.isBooked ? (
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
          /* Booked Appointment Card */
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
