"use client";

import React, { useState } from "react";
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
  Plus,
  X,
} from "lucide-react";

export const AdminDashboardScreen = () => {
  const { setPortal, demoScenario, resolvedCases, appointment, setAppointment, t, isUrdu } = useApp();

  // Active alerts mirrors Provider urgent cases count
  const isAliResolved = resolvedCases.includes("Ali Khan");
  const activeAlertsCount = demoScenario === "emergency" && !isAliResolved ? 1 : 0;

  // 1a. State-driven Clinics, Doctors, and Patients
  const [clinics, setClinics] = useState<string[]>([
    "City General Hospital",
    "Northside Community Clinic",
  ]);

  const [doctors, setDoctors] = useState([
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
  ]);

  const [patients, setPatients] = useState([
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
  ]);

  // Form states for creation
  const [showAddDoctor, setShowAddDoctor] = useState(false);
  const [newDoctorName, setNewDoctorName] = useState("");
  const [newDoctorRole, setNewDoctorRole] = useState("Clinical Specialist");
  const [newDoctorClinic, setNewDoctorClinic] = useState(clinics[0]);

  const [showAddPatient, setShowAddPatient] = useState(false);
  const [newPatientName, setNewPatientName] = useState("");
  const [newPatientCondition, setNewPatientCondition] = useState("Type 2 Diabetes");
  const [newPatientClinic, setNewPatientClinic] = useState(clinics[0]);
  const [newPatientDoctorId, setNewPatientDoctorId] = useState("PRV-002");

  const [showAddClinic, setShowAddClinic] = useState(false);
  const [newClinicName, setNewClinicName] = useState("");

  const handleAddDoctor = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDoctorName.trim()) return;
    const newId = `PRV-${String(doctors.length + 3).padStart(3, "0")}`;
    const targetClinic = newDoctorClinic || clinics[0];
    setDoctors([
      ...doctors,
      {
        id: newId,
        name: newDoctorName.trim(),
        role: newDoctorRole.trim() || "Clinical Specialist",
        clinic: targetClinic,
        assignedPatientIds: [],
      },
    ]);
    setNewDoctorName("");
    setShowAddDoctor(false);
  };

  const handleAddPatient = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPatientName.trim()) return;
    const newId = `PAT-${String(patients.length + 45).padStart(3, "0")}`;
    const targetDoctorId = newPatientDoctorId || doctors[0]?.id || "PRV-002";
    const targetClinic = newPatientClinic || clinics[0];

    const newPatient = {
      id: newId,
      name: newPatientName.trim(),
      condition: newPatientCondition.trim() || "Type 2 Diabetes",
      clinic: targetClinic,
      assignedDoctorId: targetDoctorId,
    };

    setPatients([...patients, newPatient]);

    // Update doctor's assignedPatientIds bidirectionally
    setDoctors(
      doctors.map((doc) =>
        doc.id === targetDoctorId
          ? { ...doc, assignedPatientIds: [...doc.assignedPatientIds, newId] }
          : doc
      )
    );

    setNewPatientName("");
    setShowAddPatient(false);
  };

  const handleAddClinic = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClinicName.trim()) return;
    if (!clinics.includes(newClinicName.trim())) {
      setClinics([...clinics, newClinicName.trim()]);
    }
    setNewClinicName("");
    setShowAddClinic(false);
  };

  // Schedule Entries synced with shared appointment context
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
    { action: "Admin registered new Clinic endpoint", time: "2:02 PM", type: "Configuration" },
    { action: "Admin updated staff assignment roster", time: "1:48 PM", type: "Security" },
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
          <div className="text-3xl font-bold text-teal-700 font-sans mt-1">{doctors.length}</div>
        </div>

        {/* Stat 3: Patients */}
        <div className="glass-resting rounded-2xl p-5 text-center shadow-xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
            {t.statPatients}
          </span>
          <div className="text-3xl font-bold text-navy-800 font-sans mt-1">{patients.length + 105}</div>
        </div>

        {/* Stat 4: Active Alerts */}
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

      {/* Clinic Management Banner (Item 7 & Fix 1) */}
      <div className="glass-resting rounded-3xl p-5 sm:p-6 shadow-sm border border-slate-200/90 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/80 pb-3">
          <div className="flex items-center gap-2 text-navy-800 font-heading font-bold text-base">
            <Building2 className="w-5 h-5 text-teal-700" />
            <span>Connected Healthcare Clinics & Centers</span>
          </div>
          <button
            type="button"
            onClick={() => setShowAddClinic(!showAddClinic)}
            id="add-clinic-btn"
            className="min-h-[36px] text-xs font-bold text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-xl transition-colors inline-flex items-center gap-1.5 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Add Clinic</span>
          </button>
        </div>

        {/* Inline Add Clinic Form */}
        {showAddClinic && (
          <form onSubmit={handleAddClinic} className="p-3.5 rounded-2xl bg-teal-50/80 border border-teal-200 flex flex-col sm:flex-row items-center gap-3 animate-fadeIn">
            <input
              type="text"
              placeholder="e.g. South Suburban Health Center"
              value={newClinicName}
              onChange={(e) => setNewClinicName(e.target.value)}
              id="new-clinic-name-input"
              className="w-full flex-1 px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              required
            />
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                type="submit"
                id="save-clinic-btn"
                className="flex-1 sm:flex-none min-h-[38px] px-4 py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-colors shadow-2xs"
              >
                Save Clinic
              </button>
              <button
                type="button"
                onClick={() => setShowAddClinic(false)}
                className="p-2 rounded-xl text-slate-500 hover:bg-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}

        {/* Clinics Chips */}
        <div className="flex flex-wrap gap-2 pt-1">
          {clinics.map((clinic, idx) => (
            <div
              key={idx}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200/90 text-navy-800 text-xs font-semibold shadow-2xs"
            >
              <Hospital className="w-3.5 h-3.5 text-teal-700" />
              <span>{clinic}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
            </div>
          ))}
        </div>
      </div>

      {/* Section A: Clinical Staff & Enrolled Patients (Interactive Creation) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
        {/* Doctors Directory */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Stethoscope className="w-5 h-5 text-teal-700" />
              <span>Attending Clinical Providers</span>
            </h2>
            <button
              type="button"
              onClick={() => setShowAddDoctor(!showAddDoctor)}
              id="add-doctor-btn"
              className="text-xs font-bold text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-xl transition-colors inline-flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Doctor</span>
            </button>
          </div>

          {/* Inline Add Doctor Form */}
          {showAddDoctor && (
            <form onSubmit={handleAddDoctor} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-navy-800">Register New Clinical Provider</span>
                <button type="button" onClick={() => setShowAddDoctor(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Doctor Full Name (e.g. Dr. Haris Farooq)"
                  value={newDoctorName}
                  onChange={(e) => setNewDoctorName(e.target.value)}
                  id="new-doctor-name-input"
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                  required
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Specialty (e.g. Nephrologist)"
                    value={newDoctorRole}
                    onChange={(e) => setNewDoctorRole(e.target.value)}
                    id="new-doctor-role-input"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                  />
                  <select
                    value={newDoctorClinic}
                    onChange={(e) => setNewDoctorClinic(e.target.value)}
                    id="new-doctor-clinic-select"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                  >
                    {clinics.map((c, i) => (
                      <option key={i} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                type="submit"
                id="save-doctor-btn"
                className="w-full min-h-[38px] py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-colors shadow-2xs"
              >
                Save Doctor Profile
              </button>
            </form>
          )}

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
                      {assigned.length > 0 ? (
                        assigned.map((p) => (
                          <span
                            key={p.id}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-800 text-[11px] font-medium"
                          >
                            <User className="w-3 h-3 text-teal-700" />
                            <span>{p.name}</span>
                            <span className="text-[10px] text-slate-400">({p.id})</span>
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-400 italic text-[11px]">No active patient assignments</span>
                      )}
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
            <button
              type="button"
              onClick={() => setShowAddPatient(!showAddPatient)}
              id="add-patient-btn"
              className="text-xs font-bold text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-xl transition-colors inline-flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Patient</span>
            </button>
          </div>

          {/* Inline Add Patient Form */}
          {showAddPatient && (
            <form onSubmit={handleAddPatient} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-navy-800">Enroll New Chronic Patient</span>
                <button type="button" onClick={() => setShowAddPatient(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Patient Full Name (e.g. Fatima Noor)"
                  value={newPatientName}
                  onChange={(e) => setNewPatientName(e.target.value)}
                  id="new-patient-name-input"
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                  required
                />
                <input
                  type="text"
                  placeholder="Condition (e.g. Type 2 Diabetes / HTN)"
                  value={newPatientCondition}
                  onChange={(e) => setNewPatientCondition(e.target.value)}
                  id="new-patient-condition-input"
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                  required
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Clinic</label>
                    <select
                      value={newPatientClinic}
                      onChange={(e) => setNewPatientClinic(e.target.value)}
                      id="new-patient-clinic-select"
                      className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                    >
                      {clinics.map((c, i) => (
                        <option key={i} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Attending Doctor</label>
                    <select
                      value={newPatientDoctorId}
                      onChange={(e) => setNewPatientDoctorId(e.target.value)}
                      id="new-patient-doctor-select"
                      className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-xs text-navy-800 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                    >
                      {doctors.map((d) => (
                        <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
              <button
                type="submit"
                id="save-patient-btn"
                className="w-full min-h-[38px] py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-colors shadow-2xs"
              >
                Save Patient Profile
              </button>
            </form>
          )}

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
                    ? sch.status === "Requested"
                      ? "bg-amber-50/80 border-amber-300 ring-2 ring-amber-400/30"
                      : "bg-teal-50/70 border-teal-300 ring-2 ring-teal-400/30"
                    : "bg-white/80 border-slate-200/70"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-navy-800">{sch.patient}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({sch.patientId})</span>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      sch.status === "Confirmed"
                        ? "bg-mutedGreen-100 text-mutedGreen-800 border border-mutedGreen-200"
                        : sch.status === "Requested"
                        ? "bg-amber-100 text-amber-900 border border-amber-300"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {sch.status === "Requested" ? "Patient Requested" : sch.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mt-2 pt-2 border-t border-slate-100">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Attending</span>
                    <span className="font-medium text-navy-800">{sch.provider}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Slot</span>
                    <span className={`font-medium ${sch.isLive ? (sch.status === "Requested" ? "text-amber-800 font-bold" : "text-teal-800 font-bold") : "text-slate-800"}`}>
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
