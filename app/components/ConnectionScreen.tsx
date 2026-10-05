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
} from "lucide-react";
import { api, ApiError, EHRSystemResponse, EHRConnectionResponse } from "../lib/api";

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

  // Live EHR form state
  const [ehrSystems, setEhrSystems] = useState<EHRSystemResponse[]>([]);
  const [selectedSystemId, setSelectedSystemId] = useState<string>("");
  const [patientIdInput, setPatientIdInput] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [showConnectModal, setShowConnectModal] = useState<boolean>(false);

  useEffect(() => {
    if (isLiveMode) {
      // Load EHR systems
      api
        .getEHRSystems()
        .then((systems) => {
          setEhrSystems(systems);
          if (systems.length > 0) {
            setSelectedSystemId(systems[0].ehr_system_id);
          }
        })
        .catch(() => {});

      // Load existing connection
      api
        .getEHRConnection()
        .then((conn) => {
          setLiveEhrConnection(conn);
          if (conn.mode === "fhir") {
            setConnectionMode("fhir");
          } else if (conn.mode === "isolated") {
            setConnectionMode("offline");
          }
        })
        .catch(() => {});
    }
  }, [isLiveMode, setConnectionMode, setLiveEhrConnection]);

  const handleFhirConnect = async () => {
    if (connectingFhir || fhirSuccess) return;
    setError(null);

    if (isLiveMode) {
      if (!selectedSystemId) {
        setError(t.selectEhrSystemLabel);
        return;
      }
      const cleanPatientId = patientIdInput.trim();
      if (!cleanPatientId) {
        setError("Please enter a valid Patient ID (MRN)");
        return;
      }

      setConnectingFhir(true);
      try {
        const res = await api.connectEHR(selectedSystemId, cleanPatientId);
        setLiveEhrConnection(res);
        setConnectionMode("fhir");
        setFhirSuccess(true);
        setShowConnectModal(false);
        setTimeout(() => {
          setScreen("home");
        }, 1200);
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(err?.message || "Failed to connect to EHR");
        }
      } finally {
        setConnectingFhir(false);
      }
      return;
    }

    // Mocked FHIR handshake delay (1.5s)
    setConnectingFhir(true);
    setTimeout(() => {
      setConnectingFhir(false);
      setFhirSuccess(true);
      setConnectionMode("fhir");
      setTimeout(() => {
        setScreen("home");
      }, 1200);
    }, 1500);
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

    // Proceeds to Health Profile screen in mock mode
    setTimeout(() => {
      setScreen("profile");
    }, 800);
  };

  const isConnectedToFhir = Boolean(
    liveEhrConnection?.mode === "fhir" && liveEhrConnection.connection
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
        <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
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
              <span>{t.connectedBadgeTitle}</span>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">
              HL7® FHIR® R4
            </span>
          </div>

          <div className="space-y-1">
            <h3 className="text-base font-bold text-navy-800">
              {liveEhrConnection.connection.display_name}
            </h3>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
              <span>
                <strong>{t.patientIdMasked}:</strong> {liveEhrConnection.connection.masked_patient_id}
              </span>
              {liveEhrConnection.connection.last_verified_at && (
                <span>
                  <strong>{t.lastVerified}:</strong>{" "}
                  {new Date(liveEhrConnection.connection.last_verified_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
            </div>
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
              <span>{t.disconnectEhrBtn}</span>
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
                  HL7® FHIR®
                </span>
              </div>

              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {t.fhirCardDesc}
              </p>

              {/* In Live Mode: Connect Dialog toggle */}
              {isLiveMode && !isConnectedToFhir && (
                <div className="mt-3.5 space-y-3 pt-2 border-t border-slate-100">
                  <div>
                    <label className="block text-xs font-semibold text-navy-800 mb-1">
                      {t.selectEhrSystemLabel}
                    </label>
                    <select
                      value={selectedSystemId}
                      onChange={(e) => setSelectedSystemId(e.target.value)}
                      id="ehr-system-select"
                      className="w-full text-xs rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                    >
                      {ehrSystems.map((s) => (
                        <option key={s.ehr_system_id} value={s.ehr_system_id}>
                          {s.display_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-navy-800 mb-1" htmlFor="ehr-patient-id-input">
                      {t.patientIdLabel}
                    </label>
                    <input
                      id="ehr-patient-id-input"
                      type="text"
                      value={patientIdInput}
                      onChange={(e) => setPatientIdInput(e.target.value)}
                      placeholder={t.patientIdPlaceholder}
                      className="w-full text-xs rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
                    />
                  </div>

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
