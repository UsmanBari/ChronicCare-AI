"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import {
  Hospital,
  Database,
  CheckCircle2,
  Loader2,
  ShieldCheck,
  ArrowRight,
  HardDrive,
  Unlink,
  AlertCircle,
  Link as LinkIcon,
  ShieldAlert,
  Activity,
  Info,
  Server,
} from "lucide-react";
import { api, ApiError, EHRSystemResponse, EHRConnectionResponse, EHRTestResponse } from "../lib/api";
import { describeEhrSystem, mapEhrError, mapApiError } from "../lib/presentation";

export const ConnectionScreen = () => {
  const {
    setScreen,
    setConnectionMode,
    liveEhrConnection,
    setLiveEhrConnection,
    isLiveMode,
    t,
    isUrdu,
  } = useApp();

  const [connectingFhir, setConnectingFhir] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [fhirSuccess, setFhirSuccess] = useState(false);
  const [offlineSuccess, setOfflineSuccess] = useState(false);

  // Live EHR state
  const [ehrSystems, setEhrSystems] = useState<EHRSystemResponse[]>([]);
  const [selectedSystemId, setSelectedSystemId] = useState<string>("");
  const [patientIdInput, setPatientIdInput] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Connection testing state
  const [testingSystemId, setTestingSystemId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, EHRTestResponse>>({});

  useEffect(() => {
    if (isLiveMode) {
      // Load EHR systems
      api
        .getEHRSystems()
        .then((systems) => {
          setEhrSystems(systems);
          if (systems.length > 0) {
            setSelectedSystemId(systems[0].ehr_system_id);
            // Default to first sample patient if simulated
            if (systems[0].sample_patients && systems[0].sample_patients.length > 0) {
              setPatientIdInput(systems[0].sample_patients[0].id);
            }
          }
        })
        .catch(() => {});

      // Load existing connection
      api
        .getEHRConnection()
        .then((conn) => {
          setLiveEhrConnection(conn);
          if (conn.mode === "fhir" || conn.mode === "connected") {
            setConnectionMode("fhir");
          } else if (conn.mode === "isolated") {
            setConnectionMode("offline");
          }
        })
        .catch(() => {});
    }
  }, [isLiveMode, setConnectionMode, setLiveEhrConnection]);

  const activeSystem = ehrSystems.find((s) => s.ehr_system_id === selectedSystemId);

  const handleSystemChange = (sysId: string) => {
    setSelectedSystemId(sysId);
    setError(null);
    const target = ehrSystems.find((s) => s.ehr_system_id === sysId);
    if (target?.sample_patients && target.sample_patients.length > 0) {
      setPatientIdInput(target.sample_patients[0].id);
    } else if (target?.suggested_patient_ids && target.suggested_patient_ids.length > 0) {
      setPatientIdInput(target.suggested_patient_ids[0]);
    } else {
      setPatientIdInput("");
    }
  };

  const handleTestConnection = async (sysId: string) => {
    setTestingSystemId(sysId);
    setError(null);
    try {
      const res = await api.testEHRConnection(sysId);
      setTestResults((prev) => ({ ...prev, [sysId]: res }));
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [sysId]: { ok: false, latency_ms: 0, kind: "unknown", error_code: "ehr_unreachable" },
      }));
    } finally {
      setTestingSystemId(null);
    }
  };

  const handleFhirConnect = async () => {
    if (connectingFhir || fhirSuccess) return;
    setError(null);

    if (isLiveMode) {
      if (!selectedSystemId) {
        setError(t.selectEhrSystemLabel || "Please select an EHR system.");
        return;
      }
      const cleanPatientId = patientIdInput.trim();
      if (!cleanPatientId) {
        setError("Please enter or select a Patient ID.");
        return;
      }

      setConnectingFhir(true);
      try {
        const res = await api.connectEHR(selectedSystemId, cleanPatientId);
        setLiveEhrConnection(res);
        setConnectionMode("fhir");
        setFhirSuccess(true);
        setTimeout(() => {
          setScreen("home");
        }, 1200);
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(mapApiError(err?.status, err?.message || "ehr_unreachable"));
        }
      } finally {
        setConnectingFhir(false);
      }
      return;
    }

    // Mocked mode
    setConnectingFhir(true);
    setTimeout(() => {
      setConnectingFhir(false);
      setFhirSuccess(true);
      setConnectionMode("fhir");
      setTimeout(() => {
        setScreen("home");
      }, 1200);
    }, 1200);
  };

  const handleDisconnect = async () => {
    if (disconnecting) return;
    setDisconnecting(true);
    setError(null);
    try {
      if (isLiveMode) {
        const res = await api.disconnectEHR();
        setLiveEhrConnection(res);
      }
      setConnectionMode("offline");
      setFhirSuccess(false);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.getFriendlyMessage(isUrdu));
      } else {
        setError(err?.message || "Failed to disconnect EHR");
      }
    } finally {
      setDisconnecting(false);
    }
  };

  const handleOfflineSetup = () => {
    if (connectingFhir || fhirSuccess || offlineSuccess) return;
    setOfflineSuccess(true);
    setConnectionMode("offline");

    if (isLiveMode) {
      setLiveEhrConnection({
        mode: "isolated",
        connection: null,
      });
      setTimeout(() => {
        setScreen("health_record");
      }, 800);
      return;
    }

    setTimeout(() => {
      setScreen("profile");
    }, 800);
  };

  const isConnectedToFhir = Boolean(
    (liveEhrConnection?.mode === "fhir" || liveEhrConnection?.mode === "connected") &&
      liveEhrConnection.connection
  );

  return (
    <div className="w-full max-w-lg mx-auto space-y-5 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Title */}
      <div className="text-center space-y-1.5 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-navy-800">
          {t.connectionTitle}
        </h1>
        <p className="text-xs md:text-sm text-slate-600 max-w-md mx-auto">
          {t.connectionSubtitle}
        </p>
      </div>

      {error && (
        <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2 animate-fadeIn">
          <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active EHR Connection Status Badge (If Connected in Live Mode) */}
      {isLiveMode && isConnectedToFhir && liveEhrConnection?.connection && (
        <div className="p-5 rounded-2xl bg-teal-50/80 border-2 border-teal-300 space-y-3.5 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-100 text-teal-800 text-xs font-bold">
              <ShieldCheck className="w-4 h-4 text-teal-700" />
              <span>{t.connectedBadgeTitle || "Connected Mode Active"}</span>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">
              HL7® FHIR® R4
            </span>
          </div>

          <div className="space-y-1">
            <h3 className="text-base font-bold text-navy-800">
              {liveEhrConnection.connection.display_name}
            </h3>
            <p className="text-xs text-teal-900 font-medium">
              {liveEhrConnection.record_source_label || "Connected Hospital Record"}
            </p>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600 pt-1">
              <span>
                <strong>{t.patientIdMasked || "Patient ID"}:</strong> {liveEhrConnection.connection.masked_patient_id}
              </span>
              {liveEhrConnection.connection.last_verified_at && (
                <span>
                  <strong>{t.lastVerified || "Last verified"}:</strong>{" "}
                  {new Date(liveEhrConnection.connection.last_verified_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
            </div>

            {/* Honest Warning (if empty record or missing birthdate) */}
            {liveEhrConnection.warning && (
              <div className="mt-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2">
                <Info className="w-4 h-4 text-amber-700 shrink-0" />
                <span>{mapEhrError(liveEhrConnection.warning)}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={() => setScreen("home")}
              id="continue-to-home-btn"
              className="flex-1 min-h-[40px] px-4 py-2 bg-teal-700 hover:bg-teal-600 text-white font-semibold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-2"
            >
              <span>{t.continue}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </button>
            <button
              type="button"
              onClick={handleDisconnect}
              disabled={disconnecting}
              id="disconnect-ehr-btn"
              className="min-h-[40px] px-4 py-2 bg-white hover:bg-red-50 text-red-700 border border-red-200 font-semibold text-xs rounded-xl transition-all flex items-center gap-1.5"
            >
              {disconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Unlink className="w-3.5 h-3.5" />}
              <span>{t.disconnectEhrBtn || "Disconnect"}</span>
            </button>
          </div>
        </div>
      )}

      {/* Connection Mode Selection Cards */}
      <div className="grid grid-cols-1 gap-4">
        {/* Card 1: FHIR EHR Connection */}
        <div
          className={`w-full text-left p-5 rounded-2xl border-2 transition-all relative overflow-hidden ${
            isConnectedToFhir || fhirSuccess
              ? "border-mutedGreen-800 bg-mutedGreen-50 ring-2 ring-mutedGreen-800/20"
              : connectingFhir
              ? "border-teal-600 bg-teal-50"
              : "border-slate-200 bg-white hover:border-teal-700 hover:shadow-lg"
          }`}
        >
          <div className="flex items-start gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                isConnectedToFhir || fhirSuccess
                  ? "bg-mutedGreen-800 text-white"
                  : connectingFhir
                  ? "bg-teal-700 text-white"
                  : "bg-navy-50 text-teal-700"
              }`}
            >
              {isConnectedToFhir || fhirSuccess ? (
                <CheckCircle2 className="w-6 h-6 animate-fadeIn" />
              ) : connectingFhir ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <Hospital className="w-6 h-6" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-heading text-base font-bold text-navy-800">
                  {t.fhirCardTitle}
                </h2>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-800 shrink-0">
                  HL7® FHIR® R4
                </span>
              </div>

              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {t.fhirCardDesc}
              </p>

              {/* In Live Mode: Enhanced Systems, Testing & Patient Selectors */}
              {isLiveMode && !isConnectedToFhir && (
                <div className="mt-3.5 space-y-3 pt-3 border-t border-slate-100">
                  {/* EHR System Select */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-semibold text-navy-800">
                        {t.selectEhrSystemLabel || "EHR System"}
                      </label>
                      {activeSystem && (
                        <button
                          type="button"
                          onClick={() => handleTestConnection(activeSystem.ehr_system_id)}
                          disabled={testingSystemId === activeSystem.ehr_system_id}
                          id="test-ehr-connection-btn"
                          className="text-[11px] font-semibold text-teal-700 hover:text-teal-900 inline-flex items-center gap-1"
                        >
                          {testingSystemId === activeSystem.ehr_system_id ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              <span>Testing...</span>
                            </>
                          ) : (
                            <>
                              <Activity className="w-3 h-3" />
                              <span>Test connection</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    <select
                      value={selectedSystemId}
                      onChange={(e) => handleSystemChange(e.target.value)}
                      id="ehr-system-select"
                      className="w-full text-xs rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                    >
                      {ehrSystems.map((s) => {
                        const desc = describeEhrSystem(s);
                        return (
                          <option key={s.ehr_system_id} value={s.ehr_system_id}>
                            {s.display_name} ({desc.badge})
                          </option>
                        );
                      })}
                    </select>

                    {/* Active System Description & Test Status */}
                    {activeSystem && (
                      <div className="mt-2 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-600">
                            {describeEhrSystem(activeSystem).description}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                              describeEhrSystem(activeSystem).badgeColor
                            }`}
                          >
                            {describeEhrSystem(activeSystem).badge}
                          </span>
                        </div>

                        {/* Test connection result badge */}
                        {testResults[activeSystem.ehr_system_id] && (
                          <div
                            className={`p-2 rounded-lg text-xs flex items-center justify-between ${
                              testResults[activeSystem.ehr_system_id].ok
                                ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                                : "bg-red-50 text-red-900 border border-red-200"
                            }`}
                          >
                            <span className="font-semibold">
                              {testResults[activeSystem.ehr_system_id].ok
                                ? `Online (${testResults[activeSystem.ehr_system_id].latency_ms}ms latency)`
                                : `Unavailable (${mapEhrError(testResults[activeSystem.ehr_system_id].error_code)})`}
                            </span>
                            <span className="text-[10px] uppercase font-mono font-bold">
                              {testResults[activeSystem.ehr_system_id].ok ? "HTTP 200" : "ERROR"}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Patient ID Selection: Sample dropdown vs Manual input */}
                  {activeSystem?.sample_patients && activeSystem.sample_patients.length > 0 ? (
                    <div>
                      <label className="block text-xs font-semibold text-navy-800 mb-1" htmlFor="sample-patient-select">
                        Sample Patient Profile (Synthetic Data)
                      </label>
                      <select
                        id="sample-patient-select"
                        value={patientIdInput}
                        onChange={(e) => setPatientIdInput(e.target.value)}
                        className="w-full text-xs rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                      >
                        {activeSystem.sample_patients.map((sp) => (
                          <option key={sp.id} value={sp.id}>
                            {sp.label}
                          </option>
                        ))}
                      </select>

                      {/* Selected sample patient details */}
                      {(() => {
                        const selectedSample = activeSystem.sample_patients.find((sp) => sp.id === patientIdInput);
                        if (!selectedSample) return null;
                        return (
                          <div className="mt-1.5 p-2 rounded-lg bg-purple-50/70 border border-purple-200 text-purple-950 text-[11px] leading-relaxed">
                            <strong>Profile:</strong> {selectedSample.description}
                          </div>
                        );
                      })()}
                    </div>
                  ) : (
                    <div>
                      <label className="block text-xs font-semibold text-navy-800 mb-1" htmlFor="ehr-patient-id-input">
                        {t.patientIdLabel || "Patient Identifier (UUID or MRN)"}
                      </label>
                      <input
                        id="ehr-patient-id-input"
                        type="text"
                        value={patientIdInput}
                        onChange={(e) => setPatientIdInput(e.target.value)}
                        placeholder={t.patientIdPlaceholder || "e.g. d48ac962-78c6-46cf-ba33-a24771bfa0e4"}
                        className="w-full text-xs rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
                      />

                      {/* Suggested Patient IDs */}
                      {activeSystem?.suggested_patient_ids && activeSystem.suggested_patient_ids.length > 0 && (
                        <div className="mt-2">
                          <span className="text-[11px] text-slate-500 font-medium block mb-1">
                            Verified Adult Test IDs:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {activeSystem.suggested_patient_ids.map((sugId) => (
                              <button
                                key={sugId}
                                type="button"
                                onClick={() => setPatientIdInput(sugId)}
                                className={`px-2 py-0.5 text-[10px] font-mono rounded-lg border transition-all ${
                                  patientIdInput === sugId
                                    ? "bg-blue-600 text-white border-blue-600"
                                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                                }`}
                              >
                                {sugId.slice(0, 8)}...
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Honest Clinical Testing Disclaimer */}
                  <p className="text-[11px] text-slate-500 italic pt-1">
                    Simulated hospital records use synthetic data for testing. Never enter real patient health identifiers into public sandboxes.
                  </p>

                  <button
                    type="button"
                    onClick={handleFhirConnect}
                    disabled={connectingFhir || !patientIdInput.trim()}
                    id="connect-fhir-btn"
                    className="w-full min-h-[40px] py-2 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] disabled:opacity-50 text-white font-semibold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-2"
                  >
                    {connectingFhir ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>{t.fhirConnectingText}</span>
                      </>
                    ) : (
                      <>
                        <LinkIcon className="w-4 h-4" />
                        <span>{t.connectEhrBtn}</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* In Mock Mode: Clickable card trigger */}
              {!isLiveMode && (
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={handleFhirConnect}
                    disabled={connectingFhir || fhirSuccess || offlineSuccess}
                    id="connect-fhir-btn"
                    className="min-h-[40px] px-4 py-2 bg-navy-800 hover:bg-navy-700 text-white font-semibold text-xs rounded-xl shadow-xs flex items-center gap-2"
                  >
                    {connectingFhir ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>{t.fhirConnectingText}</span>
                      </>
                    ) : fhirSuccess ? (
                      <>
                        <ShieldCheck className="w-4 h-4 text-teal-300" />
                        <span>{t.fhirConnectedText}</span>
                      </>
                    ) : (
                      <>
                        <span>Connect via FHIR</span>
                        <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Card 2: Offline / Isolated Profile Setup */}
        <button
          type="button"
          onClick={handleOfflineSetup}
          disabled={connectingFhir || fhirSuccess || offlineSuccess}
          id="connect-offline-btn"
          className={`w-full text-left p-5 rounded-2xl border-2 transition-all relative overflow-hidden group ${
            offlineSuccess || (isLiveMode && liveEhrConnection?.mode === "isolated")
              ? "border-amber-800 bg-amber-50 ring-2 ring-amber-800/20"
              : "border-slate-200 bg-white hover:border-amber-800 hover:shadow-lg active:scale-[0.99]"
          }`}
        >
          <div className="flex items-start gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                offlineSuccess || (isLiveMode && liveEhrConnection?.mode === "isolated")
                  ? "bg-amber-800 text-white"
                  : "bg-navy-50 text-navy-800 group-hover:bg-amber-800 group-hover:text-white"
              }`}
            >
              {offlineSuccess || (isLiveMode && liveEhrConnection?.mode === "isolated") ? (
                <CheckCircle2 className="w-6 h-6 animate-fadeIn" />
              ) : (
                <HardDrive className="w-6 h-6" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-heading text-base font-bold text-navy-800">
                  {t.offlineCardTitle}
                </h2>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-100 text-amber-800 shrink-0">
                  Local Store
                </span>
              </div>

              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {t.offlineCardDesc}
              </p>

              {(offlineSuccess || (isLiveMode && liveEhrConnection?.mode === "isolated")) && (
                <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-100 text-amber-800 font-semibold text-xs animate-fadeIn">
                  <Database className="w-4 h-4 text-amber-800" />
                  <span>{t.offlineConnectedText}</span>
                </div>
              )}
            </div>
          </div>
        </button>
      </div>
    </div>
  );
};
