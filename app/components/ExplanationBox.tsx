"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { api, PatientExplanation } from "../lib/api";
import { HelpCircle, ChevronDown, BookOpen, Loader2 } from "lucide-react";

interface ExplanationBoxProps {
  explanation?: PatientExplanation | null;
  emergency?: boolean;
  checkinId?: string;
  isDemo?: boolean;
}

/**
 * ExplanationBox provides an accessible, expandable "Why this result?" accordion
 * for patients to understand guideline reasoning behind their check-in findings.
 * Adheres strictly to:
 * 1. Collapsed by default.
 * 2. Never shown during emergencies or on explainer error.
 * 3. Shows "Preparing your explanation..." when status is pending, polling until ready.
 * 4. Full keyboard accessibility (Enter / Space toggles, aria-expanded, focus preserved).
 * 5. Displays clinical guideline citations without "AI" or model branding.
 */
export const ExplanationBox: React.FC<ExplanationBoxProps> = ({
  explanation: propExplanation,
  emergency: propEmergency,
  checkinId: propCheckinId,
  isDemo = false,
}) => {
  const { liveCheckinResult, activeLiveCheckin, t, isUrdu } = useApp();
  const [isOpen, setIsOpen] = useState(false);

  const initialExplanation = propExplanation !== undefined ? propExplanation : liveCheckinResult?.explanation;
  const isEmergency = propEmergency !== undefined ? propEmergency : liveCheckinResult?.emergency;
  const effectiveCheckinId = propCheckinId || activeLiveCheckin?.checkin_id;

  const [explanation, setExplanation] = useState<PatientExplanation | null | undefined>(initialExplanation);

  useEffect(() => {
    setExplanation(initialExplanation);
  }, [initialExplanation]);

  // Polling for background explanation
  useEffect(() => {
    if (isEmergency || !explanation || explanation.status !== "pending" || !effectiveCheckinId) {
      return;
    }

    let isMounted = true;
    let pollCount = 0;
    const maxPolls = 30; // 30 * 3s = 90s timeout

    const intervalId = setInterval(async () => {
      pollCount += 1;
      if (pollCount > maxPolls) {
        clearInterval(intervalId);
        if (isMounted) {
          setExplanation(null);
        }
        return;
      }

      try {
        const polled = await api.getCheckinExplanation(effectiveCheckinId);
        if (!isMounted) return;

        if (polled && polled.status === "ready") {
          setExplanation(polled);
          clearInterval(intervalId);
        } else if (polled && polled.status === "error") {
          setExplanation(null);
          clearInterval(intervalId);
        }
      } catch (err) {
        // Stop polling and hide banner on error
        if (isMounted) {
          setExplanation(null);
          clearInterval(intervalId);
        }
      }
    }, 3000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [explanation?.status, effectiveCheckinId, isEmergency]);

  // Invariant 1: Never render in emergencies
  if (isEmergency) {
    return null;
  }

  // Pending State: Accessible loading banner
  if (explanation?.status === "pending") {
    return (
      <div
        data-testid="explanation-pending"
        dir={isUrdu ? "rtl" : "ltr"}
        className={`rounded-2xl border border-teal-200/80 bg-teal-50/60 px-4 py-3 text-xs text-teal-800 flex items-center gap-2.5 shadow-2xs ${
          isUrdu ? "font-urdu text-right" : ""
        }`}
      >
        <Loader2 className="w-4 h-4 text-teal-700 animate-spin shrink-0" />
        <span className="font-medium">
          {t.explanationPending || "Preparing your explanation..."}
        </span>
      </div>
    );
  }

  // Invariant 2: Never render when explanation is absent, errored, or has no sentences
  if (!explanation || explanation.status === "error" || !explanation.sentences || explanation.sentences.length === 0) {
    return null;
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setIsOpen((prev) => !prev);
    }
  };

  const sentences = explanation.sentences || [];
  const sources = explanation.sources || [];

  return (
    <div
      data-testid="patient-explanation-box"
      dir={isUrdu ? "rtl" : "ltr"}
      className={`rounded-2xl border border-slate-200/90 bg-slate-50/70 overflow-hidden text-left transition-all shadow-2xs ${
        isUrdu ? "font-urdu text-right" : ""
      }`}
    >
      <button
        type="button"
        id="explanation-toggle-btn"
        data-testid="explanation-toggle-btn"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className="w-full min-h-[44px] px-4 py-3 flex items-center justify-between gap-3 text-slate-700 hover:text-navy-900 hover:bg-slate-100/80 transition-colors focus:outline-none focus:ring-2 focus:ring-teal-700 focus:ring-inset"
      >
        <div className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-teal-700 shrink-0" />
          <span className="text-xs font-bold">
            {isOpen ? t.hideWhyThisResultBtn : t.whyThisResultBtn}
          </span>
          {isDemo && (
            <span className="px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-600 text-[9px] font-bold uppercase tracking-wider">
              {isUrdu ? "مثال" : "Example"}
            </span>
          )}
        </div>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ${
            isOpen ? "rotate-180 text-teal-700" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div
          data-testid="explanation-content"
          className="px-4 pb-4 pt-1 space-y-3 border-t border-slate-200/70 text-xs text-slate-700 leading-relaxed animate-fadeIn"
        >
          {/* Sentences */}
          <div className="space-y-2 pt-1">
            {sentences.map((s, idx) => (
              <p key={idx} data-testid="explanation-sentence" className="leading-relaxed">
                {s.text}
              </p>
            ))}
          </div>

          {/* Formatted Sources Line */}
          {sources.length > 0 && (
            <div
              data-testid="explanation-sources"
              className="pt-2 border-t border-slate-200/60 flex items-start gap-2 text-[11px] text-slate-500"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
              <div className="space-y-1 w-full">
                <span className="font-semibold text-slate-600 block">
                  {t.explanationSourcesTitle}:
                </span>
                <ul className="space-y-1">
                  {sources.map((src, idx) => {
                    const citationText = src.full_citation || (
                      [src.edition, src.section_path, src.title].filter(Boolean).join(", ")
                    );
                    const rawDoi = src.doi?.trim();
                    const doiUrl = rawDoi && rawDoi.toUpperCase() !== "TO FILL BY USMAN"
                      ? (rawDoi.startsWith("http://") || rawDoi.startsWith("https://") ? rawDoi : `https://doi.org/${rawDoi}`)
                      : null;

                    return (
                      <li key={idx} data-testid="explanation-source-item" className="text-slate-600 leading-normal">
                        <span>{citationText}</span>
                        {doiUrl && (
                          <a
                            href={doiUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            data-testid="explanation-source-doi"
                            className="inline-flex items-center ml-1.5 text-teal-700 hover:text-teal-900 underline font-medium"
                          >
                            ({t.explanationDoiLabel || "DOI"})
                          </a>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
