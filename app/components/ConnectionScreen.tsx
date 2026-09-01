"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Hospital, Database, CheckCircle2, Loader2, ShieldCheck, ArrowRight, HardDrive } from "lucide-react";

export const ConnectionScreen = () => {
  const { setScreen, setConnectionMode, t, isUrdu } = useApp();
  const [connectingFhir, setConnectingFhir] = useState(false);
  const [fhirSuccess, setFhirSuccess] = useState(false);
  const [offlineSuccess, setOfflineSuccess] = useState(false);

  const handleFhirConnect = () => {
    if (connectingFhir || fhirSuccess) return;
    setConnectingFhir(true);

    // Mocked FHIR handshake delay (1.5s)
    setTimeout(() => {
      setConnectingFhir(false);
      setFhirSuccess(true);
      setConnectionMode("fhir");

      // Proceeds DIRECTLY to Home screen after showing success checkmark
      setTimeout(() => {
        setScreen("home");
      }, 1200);
    }, 1500);
  };

  const handleOfflineSetup = () => {
    if (connectingFhir || fhirSuccess || offlineSuccess) return;
    setOfflineSuccess(true);
    setConnectionMode("offline");

    // Proceeds to Health Profile screen (step 3)
    setTimeout(() => {
      setScreen("profile");
    }, 800);
  };

  return (
    <div className="w-full max-w-lg mx-auto space-y-5 animate-fadeIn">
      {/* Title */}
      <div className="text-center space-y-1.5 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-navy-800">
          {t.connectionTitle}
        </h1>
        <p className="text-xs md:text-sm text-slate-600 max-w-md mx-auto">
          {t.connectionSubtitle}
        </p>
      </div>

      {/* Cards Container */}
      <div className="grid grid-cols-1 gap-4">
        {/* Card 1: FHIR EHR Connection */}
        <button
          type="button"
          onClick={handleFhirConnect}
          disabled={connectingFhir || fhirSuccess || offlineSuccess}
          id="connect-fhir-btn"
          className={`w-full text-left p-5 rounded-2xl border-2 transition-all relative overflow-hidden group ${
            fhirSuccess
              ? "border-mutedGreen-800 bg-mutedGreen-50 ring-2 ring-mutedGreen-800/20"
              : connectingFhir
              ? "border-teal-600 bg-teal-50"
              : "border-slate-200 bg-white hover:border-teal-700 hover:shadow-lg active:scale-[0.99]"
          }`}
        >
          <div className="flex items-start gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                fhirSuccess
                  ? "bg-mutedGreen-800 text-white"
                  : connectingFhir
                  ? "bg-teal-700 text-white"
                  : "bg-navy-50 text-teal-700 group-hover:bg-teal-700 group-hover:text-white"
              }`}
            >
              {fhirSuccess ? (
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

              {/* Status indicator on click */}
              {connectingFhir && (
                <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-teal-700 animate-fadeIn">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{t.fhirConnectingText}</span>
                </div>
              )}

              {fhirSuccess && (
                <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-mutedGreen-100 text-mutedGreen-800 font-semibold text-xs animate-fadeIn">
                  <ShieldCheck className="w-4 h-4 text-mutedGreen-800" />
                  <span>{t.fhirConnectedText}</span>
                </div>
              )}
            </div>
          </div>
        </button>

        {/* Card 2: Offline Profile Setup */}
        <button
          type="button"
          onClick={handleOfflineSetup}
          disabled={connectingFhir || fhirSuccess || offlineSuccess}
          id="connect-offline-btn"
          className={`w-full text-left p-5 rounded-2xl border-2 transition-all relative overflow-hidden group ${
            offlineSuccess
              ? "border-amber-800 bg-amber-50 ring-2 ring-amber-800/20"
              : "border-slate-200 bg-white hover:border-amber-800 hover:shadow-lg active:scale-[0.99]"
          }`}
        >
          <div className="flex items-start gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                offlineSuccess
                  ? "bg-amber-800 text-white"
                  : "bg-navy-50 text-navy-800 group-hover:bg-amber-800 group-hover:text-white"
              }`}
            >
              {offlineSuccess ? (
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

              {offlineSuccess && (
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
