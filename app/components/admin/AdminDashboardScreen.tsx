"use client";

import React from "react";
import { useApp } from "../../context/AppContext";
import { Shield, Users, Stethoscope, User, Activity, Clock, Key, ArrowLeft, CheckCircle2, AlertOctagon, ShieldCheck } from "lucide-react";

export const AdminDashboardScreen = () => {
  const { setPortal, demoScenario, resolvedCases, t, isUrdu } = useApp();

  // Active alerts mirrors Provider urgent cases count
  const isAliResolved = resolvedCases.includes("Ali Khan");
  const activeAlertsCount = demoScenario === "emergency" && !isAliResolved ? 1 : 0;

  const users = [
    { name: "Dr. Sana Malik", role: "Clinical Provider", status: "Active", email: "dr.sanamalik@citygeneral.org" },
    { name: "Ali Khan", role: "Patient (T2D)", status: "Active", email: "ali.khan@demo.care" },
    { name: "Sara Ahmed", role: "Patient (HTN)", status: "Active", email: "sara.ahmed@demo.care" },
    { name: "Ahmed", role: "Patient (T2D/HTN)", status: "Active", email: "ahmed@demo.care" },
    { name: "Admin Lead", role: "System Administrator", status: "Active", email: "admin@citygeneral.org" },
  ];

  const auditLogs = [
    { action: "Dr. Sana Malik reviewed Ali Khan's case", time: "2:14 PM", type: "Clinical Review" },
    { action: "Admin changed role permissions for Telemetry Worker", time: "1:48 PM", type: "Security" },
    { action: "Ali Khan connected FHIR source (City General Hospital)", time: "1:31 PM", type: "Integration" },
    { action: "HL7® FHIR® Interface handshake validated (Endpoint 200 OK)", time: "1:00 PM", type: "System" },
  ];

  return (
    <div className="w-full max-w-6xl mx-auto space-y-7 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-gradient-to-br from-slate-900 via-navy-900 to-navy-800 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-slate-700/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative z-10">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-teal-400 block mb-1.5">
              System Administration
            </span>
            <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight">
              {t.adminDashboardTitle}
            </h1>
            <p className="text-sm text-slate-300 mt-1.5 max-w-lg leading-relaxed">
              {t.adminSubtitle}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setPortal("landing")}
            id="admin-exit-portal-btn"
            className="self-start sm:self-auto min-h-[48px] px-5 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-xl text-sm font-semibold border border-slate-700 transition-colors inline-flex items-center gap-2 shadow-xs"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{isUrdu ? "پورٹل سلیکشن" : "Portal Select"}</span>
          </button>
        </div>
      </div>

      {/* Telemetry Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Stat 1: Total Users */}
        <div className="glass-resting rounded-2xl p-5 text-center shadow-xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
            {t.statUsers}
          </span>
          <div className="text-3xl font-bold text-navy-800 font-sans mt-1">126</div>
        </div>

        {/* Stat 2: Providers */}
        <div className="glass-resting rounded-2xl p-5 text-center shadow-xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
            {t.statProviders}
          </span>
          <div className="text-3xl font-bold text-teal-700 font-sans mt-1">18</div>
        </div>

        {/* Stat 3: Patients */}
        <div className="glass-resting rounded-2xl p-5 text-center shadow-xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
            {t.statPatients}
          </span>
          <div className="text-3xl font-bold text-navy-800 font-sans mt-1">108</div>
        </div>

        {/* Stat 4: Active Alerts (Color + Icon + Label) */}
        <div
          key={`admin-alert-${activeAlertsCount}`}
          className={`rounded-2xl border p-5 text-center shadow-xs transition-all duration-500 animate-fadeIn ${
            activeAlertsCount > 0
              ? "bg-emergencyRed-800/90 border-emergencyRed-700 text-white ring-2 ring-emergencyRed-800/40 shadow-lg shadow-red-700/30"
              : "glass-resting text-navy-800"
          }`}
        >
          <span className={`text-xs font-bold uppercase tracking-wider block ${
            activeAlertsCount > 0 ? "text-red-100" : "text-slate-500"
          }`}>
            {t.statActiveAlerts}
          </span>
          <div
            className={`text-2xl font-bold font-sans mt-1 flex items-center justify-center gap-1.5 ${
              activeAlertsCount > 0 ? "text-white animate-pulse" : "text-slate-700"
            }`}
          >
            {activeAlertsCount > 0 ? (
              <>
                <AlertOctagon className="w-5 h-5 text-red-200" />
                <span>{activeAlertsCount} Urgent</span>
              </>
            ) : (
              <span>0</span>
            )}
          </div>
        </div>
      </div>

      {/* 2-Column Section: User Management & Audit Log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
        {/* User Management */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Users className="w-5 h-5 text-teal-700" />
              <span>{t.userManagementTitle}</span>
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              Directory
            </span>
          </div>

          <div className="divide-y divide-slate-100 text-sm">
            {users.map((user, idx) => (
              <div key={idx} className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="font-bold text-navy-800">{user.name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{user.role} • {user.email}</div>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-mutedGreen-100 text-mutedGreen-800 font-bold text-xs flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{user.status}</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Log */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Clock className="w-5 h-5 text-slate-700" />
              <span>{t.auditLogTitle}</span>
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              Immutable Log
            </span>
          </div>

          <div className="space-y-3 text-sm">
            {auditLogs.map((log, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-white/80 border border-slate-200/70 space-y-1 shadow-xs">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-bold uppercase tracking-wider text-teal-800">
                    {log.type}
                  </span>
                  <span>{log.time}</span>
                </div>
                <p className="text-navy-800 font-medium text-sm leading-relaxed">
                  {log.action}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
