"use client";

import React from "react";
import { useApp } from "../../context/AppContext";
import {
  Shield,
  Users,
  Stethoscope,
  User,
  Activity,
  Clock,
  Key,
  ArrowLeft,
  CheckCircle2,
  AlertOctagon,
  ShieldCheck,
  Calendar,
  Building2,
  Hospital,
} from "lucide-react";

export const AdminDashboardScreen = () => {
  const { setPortal, demoScenario, resolvedCases, appointment, t, isUrdu } = useApp();

  // Active alerts mirrors Provider urgent cases count
  const isAliResolved = resolvedCases.includes("Ali Khan");
  const activeAlertsCount = demoScenario === "emergency" && !isAliResolved ? 1 : 0;

  // Supervisor Requirement (Items 5, 6, 7): Explicit Doctors & Patients with assignment IDs and Clinics
  const doctors = [
    {
      id: "PRV-002",
      name: "Dr. Sana Malik",
      role: "Lead Endocrinologist",
      clinic: "City General Hospital",
      assignedPatientIds: ["PAT-014", "PAT-021", "PAT-033"],
    },
    {
      id: "PRV-007",
      name: "Dr. Tariq Mahmood",
      role: "Cardiologist",
      clinic: "Northside Community Clinic",
      assignedPatientIds: ["PAT-033"],
    },
  ];

  const patients = [
    {
      id: "PAT-014",
      name: "Ali Khan",
      condition: "Type 2 Diabetes",
      clinic: "City General Hospital",
      assignedDoctorId: "PRV-002",
    },
    {
      id: "PAT-021",
      name: "Sara Ahmed",
      condition: "Hypertension",
      clinic: "City General Hospital",
      assignedDoctorId: "PRV-002",
    },
    {
      id: "PAT-033",
      name: "Ahmed",
      condition: "T2D & Hypertension",
      clinic: "Northside Community Clinic",
      assignedDoctorId: "PRV-002",
    },
  ];

  // Supervisor Requirement (Item 8): Admin Schedule View synced with shared appointment context
  const scheduleEntries = [
    {
      id: "SCH-101",
      patient: "Ali Khan",
      patientId: "PAT-014",
      provider: appointment.provider || "Dr. Sana Malik",
      clinic: "City General Hospital",
      slot: appointment.isBooked ? appointment.slot : "Not yet booked",
      reason: appointment.isBooked ? appointment.reason : "Pending Follow-up Triage",
      isLive: appointment.isBooked,
      status: appointment.isBooked ? (appointment.status || "Confirmed") : "Pending",
    },
    {
      id: "SCH-102",
      patient: "Sara Ahmed",
      patientId: "PAT-021",
      provider: "Dr. Sana Malik",
      clinic: "City General Hospital",
      slot: "Thu, 10:30 AM",
      reason: "Routine quarterly follow-up",
      isLive: false,
      status: "Confirmed",
    },
    {
      id: "SCH-103",
      patient: "Ahmed",
      patientId: "PAT-033",
      provider: "Dr. Tariq Mahmood",
      clinic: "Northside Community Clinic",
      slot: "Fri, 02:00 PM",
      reason: "Blood pressure telemetry review",
      isLive: false,
      status: "Confirmed",
    },
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

      {/* Section A: Clinical Staff & Enrolled Patients (Explicit Assignment Relationships & Clinics) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
        {/* Doctors Directory */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Stethoscope className="w-5 h-5 text-teal-700" />
              <span>Attending Clinical Providers</span>
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-teal-50 text-teal-800 font-bold">
              {doctors.length} Attending
            </span>
          </div>

          <div className="divide-y divide-slate-100 text-sm space-y-3">
            {doctors.map((doc) => {
              const assigned = patients.filter((p) => doc.assignedPatientIds.includes(p.id));
              return (
                <div key={doc.id} className="pt-3 first:pt-0 space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-navy-800">{doc.name}</span>
                        <span className="text-[10px] text-teal-700 font-mono font-bold bg-teal-50 px-2 py-0.5 rounded">
                          {doc.id}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500 font-medium block mt-0.5">
                        {doc.role}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[11px] font-semibold flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-slate-500" />
                      {doc.clinic}
                    </span>
                  </div>

                  {/* Explicit Assigned Patients Roster */}
                  <div className="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                      Assigned Patients ({assigned.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {assigned.map((p) => (
                        <span
                          key={p.id}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-800 text-[11px] font-medium"
                        >
                          <User className="w-3 h-3 text-teal-700" />
                          <span>{p.name}</span>
                          <span className="text-[10px] text-slate-400">({p.id})</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Patients Directory */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Users className="w-5 h-5 text-teal-700" />
              <span>Enrolled Patient Cohort</span>
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-bold">
              {patients.length} Tracked
            </span>
          </div>

          <div className="divide-y divide-slate-100 text-sm space-y-3">
            {patients.map((p) => {
              const doc = doctors.find((d) => d.id === p.assignedDoctorId);
              return (
                <div key={p.id} className="pt-3 first:pt-0 space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-navy-800">{p.name}</span>
                        <span className="text-[10px] text-slate-500 font-mono font-bold bg-slate-100 px-2 py-0.5 rounded">
                          {p.id}
                        </span>
                      </div>
                      <span className="text-xs text-teal-800 font-semibold block mt-0.5">
                        {p.condition}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[11px] font-semibold flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-slate-500" />
                      {p.clinic}
                    </span>
                  </div>

                  {/* Explicit Assigned Attending Doctor */}
                  <div className="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Attending Doctor
                    </span>
                    <span className="font-semibold text-navy-800 flex items-center gap-1.5">
                      <Stethoscope className="w-3.5 h-3.5 text-teal-700" />
                      <span>{doc ? doc.name : "Unassigned"}</span>
                      {doc && <span className="text-[10px] text-slate-400 font-mono">({doc.id})</span>}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Section B: Clinical Schedule & System Audit Log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
        {/* Schedule View (Synced with shared AppContext appointment state) */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Calendar className="w-5 h-5 text-teal-700" />
              <span>Clinical Consultation Schedule</span>
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-teal-50 text-teal-800 font-bold">
              Multi-Clinic Sync
            </span>
          </div>

          <div className="space-y-3 text-sm">
            {scheduleEntries.map((sch) => (
              <div
                key={sch.id}
                className={`p-4 rounded-2xl border transition-all ${
                  sch.isLive
                    ? "bg-teal-50/70 border-teal-300 ring-2 ring-teal-400/30"
                    : "bg-white/80 border-slate-200/70"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-navy-800">{sch.patient}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({sch.patientId})</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      sch.status === "Confirmed"
                        ? "bg-mutedGreen-100 text-mutedGreen-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {sch.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mt-2 pt-2 border-t border-slate-100">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Attending</span>
                    <span className="font-medium text-navy-800">{sch.provider}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Slot</span>
                    <span className={`font-medium ${sch.isLive ? "text-teal-800 font-bold" : "text-slate-800"}`}>
                      {sch.slot}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-500 mt-1.5 flex items-center justify-between">
                  <span className="truncate">{sch.reason}</span>
                  <span className="text-[10px] text-slate-400 shrink-0">{sch.clinic}</span>
                </div>
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
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-bold">
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
