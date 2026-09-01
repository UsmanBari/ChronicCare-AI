"use client";

import React from "react";
import { useApp } from "../../context/AppContext";
import { Shield, Users, Stethoscope, User, Activity, Clock, Key, ArrowLeft, CheckCircle2 } from "lucide-react";

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
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn py-2">
      {/* Header */}
      <div className="bg-slate-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-teal-400 block mb-1">
              System Administration
            </span>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-white">
              {t.adminDashboardTitle}
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-md">
              {t.adminSubtitle}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setPortal("landing")}
            id="admin-exit-portal-btn"
            className="self-start sm:self-auto px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs font-semibold border border-slate-700 transition-colors inline-flex items-center gap-1.5"
          >
            <ArrowLeft className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{isUrdu ? "پورٹل سلیکشن" : "Portal Select"}</span>
          </button>
        </div>
      </div>

      {/* Telemetry Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Stat 1: Total Users */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 text-center shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
            {t.statUsers}
          </span>
          <div className="text-2xl font-bold text-navy-800 font-sans mt-0.5">126</div>
        </div>

        {/* Stat 2: Providers */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 text-center shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
            {t.statProviders}
          </span>
          <div className="text-2xl font-bold text-teal-700 font-sans mt-0.5">18</div>
        </div>

        {/* Stat 3: Patients */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 text-center shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
            {t.statPatients}
          </span>
          <div className="text-2xl font-bold text-navy-800 font-sans mt-0.5">108</div>
        </div>

        {/* Stat 4: Active Alerts */}
        <div
          key={`admin-alert-${activeAlertsCount}`}
          className={`rounded-2xl border p-4 text-center shadow-xs transition-all duration-500 animate-fadeIn ${
            activeAlertsCount > 0
              ? "bg-red-950/90 border-red-500 text-white ring-2 ring-red-500/40 shadow-lg shadow-red-600/30"
              : "bg-white border-slate-200 text-navy-800"
          }`}
        >
          <span className={`text-[10px] font-bold uppercase tracking-wider block ${
            activeAlertsCount > 0 ? "text-red-200" : "text-slate-500"
          }`}>
            {t.statActiveAlerts}
          </span>
          <div
            className={`text-2xl font-bold font-sans mt-0.5 ${
              activeAlertsCount > 0 ? "text-white animate-pulse" : "text-slate-700"
            }`}
          >
            {activeAlertsCount > 0 ? `🔴 ${activeAlertsCount} Urgent` : "0"}
          </div>
        </div>
      </div>

      {/* 2-Column Section: User Management & Audit Log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Management */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Users className="w-4 h-4 text-teal-700" />
              <span>{t.userManagementTitle}</span>
            </h2>
            <span className="text-xs text-slate-500">Directory</span>
          </div>

          <div className="divide-y divide-slate-100 text-xs">
            {users.map((user, idx) => (
              <div key={idx} className="py-2.5 flex items-center justify-between">
                <div>
                  <div className="font-bold text-navy-800">{user.name}</div>
                  <div className="text-[11px] text-slate-500">{user.role}</div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-mutedGreen-100 text-mutedGreen-800 font-bold text-[10px]">
                  {user.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Log */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-700" />
              <span>{t.auditLogTitle}</span>
            </h2>
            <span className="text-xs text-slate-500">Immutable Log</span>
          </div>

          <div className="space-y-2.5 text-xs">
            {auditLogs.map((log, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="font-bold uppercase tracking-wider text-teal-800">
                    {log.type}
                  </span>
                  <span>{log.time}</span>
                </div>
                <p className="text-navy-800 font-medium text-[11px] leading-relaxed">
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
