"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { TraceStepItem } from "../../lib/api";
import {
  GitCommit,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

interface DecisionTimelineProps {
  trace?: TraceStepItem[] | null;
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({ trace }) => {
  const { t, isUrdu } = useApp();
  const [expanded, setExpanded] = useState(false);

  if (!trace || trace.length === 0) {
    return null;
  }

  // Node name mapping to friendly clinical words
  const getNodeLabel = (nodeName: string): string => {
    switch (nodeName) {
      case "node_intake":
        return t.traceNodeIntake;
      case "node_fetch_prior":
        return t.traceNodeFetchPrior;
      case "node_build_bundles":
        return t.traceNodeBuildBundles;
      case "node_reconcile":
        return t.traceNodeReconcile;
      case "node_verify":
        return t.traceNodeVerify;
      case "node_persist_local":
        return t.traceNodePersistLocal;
      case "node_decide_triage":
        return t.traceNodeDecideTriage;
      case "node_risk":
        return t.traceNodeRisk;
      case "node_explain":
        return t.traceNodeExplain;
      case "node_persist":
        return t.traceNodePersist;
      default:
        return nodeName.replace(/^node_/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  const isEmergencyShortcut = (summaryText: string): boolean => {
    const s = (summaryText || "").toLowerCase();
    return (
      s.includes("emergency=true") ||
      s.includes("emergency path") ||
      s.includes("reconciliation skipped")
    );
  };

  const visibleSteps = expanded ? trace : trace.slice(0, 3);
  const hasMore = trace.length > 3;

  return (
    <div
      className="p-5 sm:p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4"
      data-testid="decision-timeline-block"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <GitCommit className="w-5 h-5 text-teal-700" />
          <div>
            <h3 className="text-sm font-bold text-navy-800">
              {t.decisionTimelineTitle}
            </h3>
            <p className="text-[11px] text-slate-500">
              {t.decisionTimelineSubtitle}
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200 self-start sm:self-auto">
          {trace.length} {isUrdu ? "مراحل" : "steps"}
        </span>
      </div>

      {/* Vertical Steps */}
      <div className="relative pl-6 sm:pl-7 border-l-2 border-teal-100 space-y-4 pt-1">
        {visibleSteps.map((step, idx) => {
          const emergencyHit = isEmergencyShortcut(step.summary);
          const friendlyNode = getNodeLabel(step.node);

          return (
            <div
              key={idx}
              className="relative space-y-1.5"
              data-testid="trace-step-item"
            >
              {/* Bullet Node Icon */}
              <div
                className={`absolute -left-[31px] sm:-left-[35px] top-0.5 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white ${
                  emergencyHit
                    ? "border-rose-500 text-rose-600 bg-rose-50"
                    : "border-teal-600 text-teal-700"
                }`}
              >
                {emergencyHit ? (
                  <AlertTriangle className="w-3 h-3 text-rose-600" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-700" />
                )}
              </div>

              {/* Step Title & Duration */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-navy-800">
                  {friendlyNode}
                </span>
                <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                  {step.duration_ms !== undefined && step.duration_ms !== null && (
                    <span className="bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded">
                      {step.duration_ms} ms
                    </span>
                  )}
                  {step.started_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {step.started_at.includes("T")
                        ? step.started_at.split("T")[1].replace("Z", "")
                        : step.started_at}
                    </span>
                  )}
                </div>
              </div>

              {/* Emergency Shortcut Badge */}
              {emergencyHit && (
                <div
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-[11px] font-semibold"
                  data-testid="trace-emergency-shortcut"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  <span>{t.traceEmergencyShortcut}</span>
                </div>
              )}

              {/* Summary Text (Counts and Levels Only, No Names or Readings) */}
              <p className="text-xs text-slate-600 leading-relaxed font-mono text-[11px] bg-slate-50/70 p-2 rounded-xl border border-slate-200/80">
                {step.summary}
              </p>
            </div>
          );
        })}
      </div>

      {/* Expand / Collapse Button */}
      {hasMore && (
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            data-testid="trace-toggle-btn"
            className="w-full py-2 px-3 text-xs font-semibold text-teal-800 hover:text-teal-900 bg-teal-50/80 hover:bg-teal-100/70 border border-teal-200/80 rounded-xl transition-all flex items-center justify-center gap-1.5"
          >
            <span>{expanded ? t.traceShowFewer : t.traceShowAll}</span>
            {expanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      )}
    </div>
  );
};

