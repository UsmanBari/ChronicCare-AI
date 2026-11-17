"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  FileText,
  HelpCircle,
  Info,
  Activity,
  CheckCircle2,
  Pill,
} from "lucide-react";
import {
  describeSide,
  describeMedicationItem,
  isObservationDiscrepancy,
  isObservationThatMatters,
  formatObservationTitle,
  findOlderHospitalReading,
} from "../lib/presentation";
import { getReadingStatus } from "../lib/referenceRanges";

export const ConflictScreen = () => {
  const { setScreen, checkIn, liveCheckinResult, liveEhrConnection, isLiveMode, t, isUrdu, language } = useApp();
  const isRomanUrdu = (language as string) === "roman_ur";

  // In live mode, extract comparisons and verifications
  const obsComparisons = React.useMemo(
    () => liveCheckinResult?.reconciliation?.observation_comparisons || [],
    [liveCheckinResult]
  );
  const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
  const medVerifications = liveCheckinResult?.verification?.medication_verifications || [];

  const rawMedItems: Array<{
    desc: ReturnType<typeof describeMedicationItem>;
    comparison: any;
    verification: any;
  }> = isLiveMode
    ? medComparisons.map((c: any) => {
        const v = medVerifications.find((ver: any) => ver.medication_name === c.medication_name);
        return {
          desc: describeMedicationItem(c, v, isUrdu, language),
          comparison: c,
          verification: v,
        };
      })
    : [];

  // Deduplicate medicines by normalized name (case-insensitive)
  const dedupeMedItems = (items: typeof rawMedItems) => {
    const map = new Map<string, (typeof rawMedItems)[0]>();
    for (const item of items) {
      const key = (item.comparison?.medication_name || item.desc.title || "").trim().toLowerCase();
      const existing = map.get(key);
      if (!existing) {
        map.set(key, item);
      } else {
        // If one is flagged and the other is confirmed, keep flagged for clinical review
        if (existing.desc.isConfirmed && !item.desc.isConfirmed) {
          map.set(key, item);
        }
      }
    }
    return Array.from(map.values());
  };

  const flaggedMedItems = dedupeMedItems(rawMedItems.filter((m) => !m.desc.isConfirmed));
  const confirmedMedItems = dedupeMedItems(rawMedItems.filter((m) => m.desc.isConfirmed));

  // Discrepancy comparisons that matter (BP, glucose, HbA1c) comparing hospital value to today's reading
  const discrepancyComparisons = React.useMemo(() => {
    return isLiveMode ? obsComparisons.filter(isObservationDiscrepancy) : [];
  }, [isLiveMode, obsComparisons]);

  // If no discrepancies, check for first-checkin (missing_in_a) for an observation that matters
  const firstCheckinComparisons = React.useMemo(() => {
    return isLiveMode && discrepancyComparisons.length === 0
      ? obsComparisons.filter(
          (c: any) =>
            isObservationThatMatters(c.observation_type) &&
            c.status === "missing_in_a" &&
            c.value_b !== null &&
            c.value_b !== undefined
        )
      : [];
  }, [isLiveMode, discrepancyComparisons, obsComparisons]);

  const combinedFirstCheckin = React.useMemo(() => {
    const list: any[] = [];
    let bpSys: any = null;
    let bpDia: any = null;

    for (const c of firstCheckinComparisons) {
      const t = (c.observation_type || "").toLowerCase();
      if (t.includes("systolic") || t === "blood_pressure_systolic") {
        bpSys = c;
      } else if (t.includes("diastolic") || t === "blood_pressure_diastolic") {
        bpDia = c;
      } else {
        list.push(c);
      }
    }

    if (bpSys && bpDia) {
      list.unshift({
        observation_type: "blood_pressure",
        value_b: `${bpSys.value_b}/${bpDia.value_b}`,
        unit_b: "mmHg",
        source_b: bpSys.source_b,
        status: "missing_in_a",
        _sys: bpSys,
        _dia: bpDia,
      });
    } else if (bpSys) {
      list.unshift(bpSys);
    } else if (bpDia) {
      list.unshift(bpDia);
    }

    return list;
  }, [firstCheckinComparisons]);

  const hasOlderHospitalReadings = React.useMemo(() => {
    return firstCheckinComparisons.some((c: any) =>
      Boolean(findOlderHospitalReading(c.observation_type, obsComparisons))
    );
  }, [firstCheckinComparisons, obsComparisons]);

  const hasObsComparisons = isLiveMode
    ? discrepancyComparisons.length > 0 || firstCheckinComparisons.length > 0
    : true;

  const isAllPlainConflicts =
    isLiveMode &&
    discrepancyComparisons.length > 0 &&
    discrepancyComparisons.every((c: any) => c.status === "conflict");

  const isMissingBaselineA = isLiveMode && firstCheckinComparisons.length > 0;
  let severity = isLiveMode ? (liveCheckinResult?.max_severity || null) : "medium";

  // Mock-mode fallback values
  let sideALabel = isUrdu ? "ماخذ ۱: پہلے درج کردہ ریکارڈ" : isRomanUrdu ? "Source A: Purana Record" : "Source A: Earlier Record";
  let sideBLabel = isUrdu ? "ماخذ ۲: آج کا چیک ان" : isRomanUrdu ? "Source B: Aaj ka Check-in" : "Source B: Today's Check-in";
  let sideAValue = isLiveMode ? "" : "180 mg/dL";
  let sideBValue = isLiveMode ? "" : "140 mg/dL";
  let sideADesc = isLiveMode ? "" : (isUrdu ? "خون میں شوگر (گلوکوز): 180 mg/dL" : isRomanUrdu ? "Glucose reading: 180 mg/dL" : "Glucose reading: 180 mg/dL");
  let sideBDesc = isLiveMode ? "" : (isUrdu ? "آج کا جواب: 140 mg/dL" : isRomanUrdu ? "Aaj ka jawab: 140 mg/dL" : "Today's check-in: 140 mg/dL");

  // Extract all clinical readings entered today (glucose, blood pressure, etc.) with target tags
  const todayReadingsList = React.useMemo(() => {
    if (!isLiveMode) {
      return [
        {
          key: "glucose",
          label: isUrdu ? "خون میں گلوکوز (شوگر)" : isRomanUrdu ? "Blood Glucose" : "Blood Glucose",
          value: sideBValue || "140 mg/dL",
          targetTag: getReadingStatus("blood_glucose", 140, language as any, "mg/dL"),
        },
      ];
    }

    const list: Array<{ key: string; label: string; value: string; targetTag?: ReturnType<typeof getReadingStatus> }> = [];
    const seen = new Set<string>();

    // 1. From observation comparisons (where value_b is provided)
    // First check for combined BP if systolic and diastolic are both in obsComparisons
    const sbpComp = obsComparisons.find((c: any) => c.observation_type?.toLowerCase().includes("systolic") && c.value_b !== null && c.value_b !== undefined);
    const dbpComp = obsComparisons.find((c: any) => c.observation_type?.toLowerCase().includes("diastolic") && c.value_b !== null && c.value_b !== undefined);

    if (sbpComp && dbpComp) {
      seen.add("systolic_blood_pressure");
      seen.add("diastolic_blood_pressure");
      seen.add("blood_pressure_systolic");
      seen.add("blood_pressure_diastolic");
      seen.add("blood_pressure");
      const sbpVal = typeof sbpComp.value_b === "number" && Number.isInteger(sbpComp.value_b) ? sbpComp.value_b : sbpComp.value_b;
      const dbpVal = typeof dbpComp.value_b === "number" && Number.isInteger(dbpComp.value_b) ? dbpComp.value_b : dbpComp.value_b;
      const bpValStr = `${sbpVal}/${dbpVal} mmHg`;
      const sbpStatus = getReadingStatus("systolic_blood_pressure", sbpComp.value_b, language as any);
      const dbpStatus = getReadingStatus("diastolic_blood_pressure", dbpComp.value_b, language as any);
      const combinedTag = (sbpStatus.status === "above_target" || dbpStatus.status === "above_target")
        ? sbpStatus.status === "above_target" ? sbpStatus : dbpStatus
        : (sbpStatus.status === "below_target" || dbpStatus.status === "below_target")
        ? sbpStatus.status === "below_target" ? sbpStatus : dbpStatus
        : sbpStatus;

      list.push({
        key: "bp",
        label: isUrdu ? "بلڈ پریشر" : isRomanUrdu ? "Blood Pressure" : "Blood Pressure",
        value: bpValStr,
        targetTag: combinedTag,
      });
    }

    // 2. Other observations in comparisons with value_b
    for (const c of obsComparisons) {
      if (c.value_b === null || c.value_b === undefined) continue;
      const normType = (c.observation_type || "").toLowerCase();
      if (seen.has(normType)) continue;
      seen.add(normType);

      const valFormatted = `${typeof c.value_b === "number" && Number.isInteger(c.value_b) ? c.value_b : c.value_b} ${c.unit_b || ""}`.trim();
      const status = getReadingStatus(c.observation_type, c.value_b, language as any, c.unit_b || "mg/dL");

      list.push({
        key: normType,
        label: formatObservationTitle(c.observation_type, isUrdu),
        value: valFormatted,
        targetTag: status,
      });
    }

    // 3. Fallback to intakes if comparisons didn't capture a reading (e.g. BP was in intake but not reconciled)
    const intakes = liveCheckinResult?.intakes || [];
    for (const it of intakes) {
      const data = it?.extracted_data || it?.readings || {};
      const sbp = data.blood_pressure_systolic ?? data.systolic ?? (Array.isArray(data.blood_pressure) ? data.blood_pressure[0] : null);
      const dbp = data.blood_pressure_diastolic ?? data.diastolic ?? (Array.isArray(data.blood_pressure) ? data.blood_pressure[1] : null);
      if (sbp !== null && sbp !== undefined && dbp !== null && dbp !== undefined && !seen.has("blood_pressure")) {
        seen.add("blood_pressure");
        seen.add("systolic_blood_pressure");
        seen.add("diastolic_blood_pressure");
        const sbpInt = typeof sbp === "number" && Number.isInteger(sbp) ? sbp : sbp;
        const dbpInt = typeof dbp === "number" && Number.isInteger(dbp) ? dbp : dbp;
        const sbpStatus = getReadingStatus("systolic_blood_pressure", sbp, language as any);
        const dbpStatus = getReadingStatus("diastolic_blood_pressure", dbp, language as any);
        const combinedTag = (sbpStatus.status === "above_target" || dbpStatus.status === "above_target")
          ? sbpStatus.status === "above_target" ? sbpStatus : dbpStatus
          : (sbpStatus.status === "below_target" || dbpStatus.status === "below_target")
          ? sbpStatus.status === "below_target" ? sbpStatus : dbpStatus
          : sbpStatus;
        list.push({
          key: "bp_intake",
          label: isUrdu ? "بلڈ پریشر" : isRomanUrdu ? "Blood Pressure" : "Blood Pressure",
          value: `${sbpInt}/${dbpInt} mmHg`,
          targetTag: combinedTag,
        });
      }

      const g = data.glucose;
      if (g !== null && g !== undefined && !seen.has("blood_glucose") && !seen.has("glucose")) {
        seen.add("blood_glucose");
        const gInt = typeof g === "number" && Number.isInteger(g) ? g : g;
        list.push({
          key: "glucose_intake",
          label: isUrdu ? "خون میں گلوکوز (شوگر)" : isRomanUrdu ? "Blood Glucose" : "Blood Glucose",
          value: `${gInt} mg/dL`,
          targetTag: getReadingStatus("blood_glucose", g, language as any, "mg/dL"),
        });
      }
    }

    return list;
  }, [isLiveMode, obsComparisons, liveCheckinResult, language, isUrdu, isRomanUrdu, sideBValue]);

  const screenTitle = isLiveMode
    ? isAllPlainConflicts
      ? t.readingDiffersTitle
      : t.needsClinicianReviewTitle
    : t.conflictDetectedTitle;

  return (
    <div
      className="w-full max-w-xl mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Clinical Alert Header */}
      <div className="bg-amber-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        {!isLiveMode && (
          <div className="mb-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-900/80 text-amber-200 text-[11px] font-bold border border-amber-600/50 uppercase tracking-wider">
              {t.demoSimulationBadge}
            </span>
          </div>
        )}
        <div className="w-14 h-14 rounded-2xl bg-amber-700/90 border border-amber-500/40 flex items-center justify-center mx-auto mb-3 shadow-md">
          <AlertTriangle className="w-8 h-8 text-amber-200" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
          {screenTitle}
        </h1>
        {severity && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-900/50 text-amber-100 text-xs font-semibold border border-amber-600/40">
            <ShieldAlert className="w-4 h-4 text-amber-300" />
            <span>{isUrdu ? `شدت: ${severity.toUpperCase()}` : `Severity: ${severity.toUpperCase()}`}</span>
          </div>
        )}
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Context Narrative */}
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-navy-800">
            {isLiveMode
              ? isMissingBaselineA
                ? hasOlderHospitalReadings
                  ? (isUrdu
                      ? "ہسپتال کا پچھلا ریکارڈ ۴۸ گھنٹے سے پرانا ہے، اس لیے طبی معالج اس کا جائزہ لیں گے۔"
                      : "Hospital records on file are older than 48 hours, so a clinician will review today's check-in.")
                  : t.firstCheckinNoRecordTitle
                : hasObsComparisons
                ? isUrdu
                  ? "آپ کے آج کے چیک ان اور پہلے سے موجود ریکارڈ کے درمیان فرق پایا گیا ہے۔"
                  : "A difference was noted between today's check-in and your saved health record."
                : t.needsClinicianReviewTitle
              : isUrdu
              ? "مریض کی درج کردہ معلومات اور اسپتال کے ریکارڈ کے درمیان تضاد پایا گیا ہے۔"
              : "A discrepancy has been detected between patient-reported telemetry and hospital records."}
          </p>
          <p className="text-xs text-slate-500">
            {isLiveMode && isMissingBaselineA
              ? hasOlderHospitalReadings
                ? (isUrdu
                    ? "ریڈنگز کا موازنہ ۴۸ گھنٹوں کے اندر کیا جاتا ہے۔ معالج فالو اپ طے کر سکتے ہیں۔"
                    : "Readings are compared within 48 hours. A clinician will review today's readings.")
                : t.firstCheckinNoRecordDesc
              : isUrdu
              ? "طبی معالج کے جائزے کے لیے کیس بھیج دیا گیا ہے۔"
              : "Flagged for clinician review to ensure longitudinal safety."}
          </p>
        </div>

        {/* Structured Source Comparison Grid: ONE card per discrepancy that matters (BP, glucose, HbA1c) */}
        {(!isLiveMode || hasObsComparisons) && (
          <div className="space-y-4">
            {/* Live Mode: One card per discrepancy that matters */}
            {isLiveMode && discrepancyComparisons.length > 0 &&
              discrepancyComparisons.map((c: any, idx: number) => {
                const tsA = c.timestamp_a || c.timestamp;
                const dateA = tsA ? tsA.slice(0, 10) : "";
                const timeA = tsA && tsA.length > 10 ? tsA.slice(0, 16).replace("T", " ") : dateA;

                const isEarlierCheckin =
                  c.source_a === "checkin" ||
                  c.source_a === "prior_checkin" ||
                  Boolean(c.source_record_id_a && c.source_record_id_a.startsWith("CHECKIN-"));

                const isSavedBaseline =
                  c.source_a === "local" ||
                  Boolean(
                    c.source_record_id_a &&
                      (c.source_record_id_a.startsWith("local-obs-") || c.source_record_id_a.startsWith("bs-"))
                  );

                let itemSideALabel = "";
                if (isEarlierCheckin) {
                  itemSideALabel = `${t.earlierCheckinLabel}${timeA ? `, ${timeA}` : ""}`;
                } else if (isSavedBaseline) {
                  itemSideALabel = `${t.savedReadingLabel}${dateA ? `, ${dateA}` : ""}`;
                } else {
                  itemSideALabel = describeSide("a", c.source_a, null, liveEhrConnection?.mode, null, tsA, isUrdu);
                }

                const itemSideAVal = `${c.value_a} ${c.unit_a || ""}`.trim();
                const itemSideADesc = `${formatObservationTitle(c.observation_type, isUrdu)}: ${itemSideAVal}`;

                const itemSideBLabel = describeSide("b", c.source_b, null, liveEhrConnection?.mode, null, null, isUrdu);
                const itemSideBVal = `${c.value_b} ${c.unit_b || ""}`.trim();
                const itemSideBDesc = isUrdu ? `آج کا جواب: ${itemSideBVal}` : `Your answer today: ${itemSideBVal}`;
                const itemBStatus = getReadingStatus(c.observation_type, c.value_b, language as any, c.unit_b || "mg/dL");
                const normObsType = (c.observation_type || "").toLowerCase();
                const otherReadings = todayReadingsList.filter(
                  (r) => !r.key.includes(normObsType) && !normObsType.includes(r.key)
                );

                return (
                  <div key={idx} className="space-y-2 p-3 sm:p-4 rounded-2xl bg-white/70 border border-slate-200/90 shadow-xs">
                    {discrepancyComparisons.length > 1 && (
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
                          <Activity className="w-3.5 h-3.5 text-teal-700" />
                          {formatObservationTitle(c.observation_type, isUrdu)}
                        </span>
                        {c.delta !== null && c.delta !== undefined && (
                          <span className="text-[11px] font-semibold text-slate-500">
                            Delta: {c.delta} {c.unit_a || c.unit_b || ""}
                          </span>
                        )}
                      </div>
                    )}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Side A: Earlier / Hospital Record */}
                      <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2 text-left">
                        <div className="flex items-center justify-between">
                          <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5" />
                            {itemSideALabel}
                          </span>
                        </div>
                        <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
                          {itemSideAVal}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {itemSideADesc}
                        </p>
                      </div>

                      {/* Side B: Today's Check-in */}
                      <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2 text-left">
                        <div className="flex items-center justify-between">
                          <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                            <Activity className="w-3.5 h-3.5" />
                            {itemSideBLabel}
                          </span>
                          {itemBStatus.status !== "unspecified" && (
                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${itemBStatus.badgeClass}`}>
                              {itemBStatus.label}
                            </span>
                          )}
                        </div>
                        <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
                          {itemSideBVal}
                        </div>
                        <p className="text-xs text-amber-950 leading-relaxed">
                          {itemSideBDesc}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}

            {/* Live Mode: First check-in with no baseline on file */}
            {isLiveMode && combinedFirstCheckin.length > 0 &&
              combinedFirstCheckin.map((c: any, idx: number) => {
                const itemSideBLabel = describeSide("b", c.source_b, null, liveEhrConnection?.mode, null, null, isUrdu);
                const itemSideBVal = `${c.value_b} ${c.unit_b || ""}`.trim();
                const itemSideBDesc = isUrdu ? `آج کا جواب: ${itemSideBVal}` : `Your answer today: ${itemSideBVal}`;
                const itemBStatus = getReadingStatus(c.observation_type, c.value_b, language as any, c.unit_b || "mg/dL");

                const older = findOlderHospitalReading(c.observation_type, obsComparisons);

                const itemSideALabel = older
                  ? (isUrdu ? "ہسپتال کا پرانا ریکارڈ" : "Hospital EHR (Older Record)")
                  : (isUrdu ? "ہسپتال کا ریکارڈ" : "Hospital EHR");

                const itemSideAVal = older
                  ? `${older.value} ${older.unit}`.trim()
                  : t.notOnFile;

                const itemSideADesc = older
                  ? (isUrdu
                      ? `آخری ہسپتال کی ریڈنگ: ${older.value} ${older.unit} (${older.date}) — موازنہ کے لیے بہت پرانی ہے (ریڈنگز کا ۴۸ گھنٹوں کے اندر موازنہ کیا جاتا ہے)`
                      : `Last hospital reading: ${older.value} ${older.unit} (${older.date}) — too old to compare (readings are compared within 48 hours)`)
                  : (isUrdu
                      ? "ہسپتال EHR: کوئی پچھلا ریکارڈ موجود نہیں — یہ مریض کا پہلا چیک ان ہے"
                      : "Hospital EHR: No prior reading on file — this is the patient's first check-in");

                return (
                  <div key={idx} className="space-y-2 p-3 sm:p-4 rounded-2xl bg-white/70 border border-slate-200/90 shadow-xs">
                    {combinedFirstCheckin.length > 1 && (
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
                          <Activity className="w-3.5 h-3.5 text-teal-700" />
                          {formatObservationTitle(c.observation_type, isUrdu)}
                        </span>
                      </div>
                    )}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2 text-left" data-testid={`first-checkin-card-a-${idx}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5" />
                            {itemSideALabel}
                          </span>
                          {older && (
                            <span className="text-[10px] font-semibold text-slate-500 font-mono">
                              {older.date}
                            </span>
                          )}
                        </div>
                        <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
                          {itemSideAVal}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed" data-testid={`first-checkin-desc-${idx}`}>
                          {itemSideADesc}
                        </p>
                      </div>

                      <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2 text-left">
                        <div className="flex items-center justify-between">
                          <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                            <Activity className="w-3.5 h-3.5" />
                            {itemSideBLabel}
                          </span>
                          {itemBStatus.status !== "unspecified" && (
                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${itemBStatus.badgeClass}`}>
                              {itemBStatus.label}
                            </span>
                          )}
                        </div>
                        <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
                          {itemSideBVal}
                        </div>
                        <p className="text-xs text-amber-950 leading-relaxed">
                          {itemSideBDesc}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}

            {/* Mock Mode Single Comparison Grid */}
            {!isLiveMode && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Side A: Earlier Record */}
                <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2 text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" />
                      {sideALabel}
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
                    {sideAValue}
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {sideADesc}
                  </p>
                </div>

                {/* Side B: Today's Check-in */}
                <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2 text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                      <Activity className="w-3.5 h-3.5" />
                      {sideBLabel}
                    </span>
                  </div>
                  <div className="flex items-center justify-between flex-wrap gap-2 pt-1">
                    <div className="text-2xl font-bold text-navy-800 font-mono">
                      {sideBValue}
                    </div>
                    {todayReadingsList[0]?.targetTag && todayReadingsList[0].targetTag.status !== "unspecified" && (
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${todayReadingsList[0].targetTag.badgeClass}`}>
                        {todayReadingsList[0].targetTag.label}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-amber-950 leading-relaxed">
                    {sideBDesc}
                  </p>
                </div>
              </div>
            )}

            {/* Single "Also reported today" section at the bottom of the section */}
            {isLiveMode && todayReadingsList.length > 0 && (
              <div
                data-testid="also-reported-today-section"
                className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-left space-y-2 mt-3"
              >
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600 block">
                  {isUrdu ? "آج کی دیگر ریڈنگز:" : isRomanUrdu ? "Aaj ki deegar readings:" : "Also reported today:"}
                </span>
                <div className="space-y-1.5">
                  {todayReadingsList.map((r, rIdx) => (
                    <div key={rIdx} className="flex items-center justify-between text-xs py-1 border-b border-amber-200/50 last:border-none">
                      <span className="text-slate-800 font-medium">
                        {r.label}: <strong className="font-mono text-navy-900">{r.value}</strong>
                      </span>
                      {r.targetTag && r.targetTag.status !== "unspecified" && (
                        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${r.targetTag.badgeClass}`}>
                          {r.targetTag.label}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Live mode with NO observation comparisons: honest clinical explanation card */}
        {isLiveMode && !hasObsComparisons && (
          <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 text-left space-y-2">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-teal-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                {t.needsClinicianReviewTitle}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {t.clinicianReviewAnswers}
            </p>
          </div>
        )}

        {/* Confirmed Medicines Section (Part 7: Calm, never flagged, deduped display) */}
        {isLiveMode && confirmedMedItems.length > 0 && (
          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-300 text-left space-y-2 animate-fadeIn">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-950 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-700" />
              <span>{isUrdu ? "تصدیق شدہ ادویات:" : isRomanUrdu ? "Tasdeeq shuda dawaiyan:" : "Confirmed medicines:"}</span>
            </span>
            <div className="space-y-1.5">
              {confirmedMedItems.map((item, idx) => {
                const details = item.desc.recordText
                  .replace(/^Record:\s*/i, "")
                  .replace(new RegExp(`^${item.desc.title}[,:\\s]*`, "i"), "");
                return (
                  <div key={idx} className="p-2.5 rounded-xl bg-white border border-emerald-200 text-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Pill className="w-3.5 h-3.5 text-emerald-700" />
                      <span className="font-bold text-navy-900">{item.desc.title}</span>
                      {details && <span className="text-slate-600">{details}</span>}
                    </div>
                    <span className="text-[11px] font-semibold text-emerald-800">
                      {item.desc.reason}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Medication Comparison Items Flagged for Review (deduped display) */}
        {isLiveMode && flaggedMedItems.length > 0 && (
          <div className="space-y-3 pt-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
              {isUrdu ? "جائزے کے لیے بھیجی گئی ادویات:" : isRomanUrdu ? "Jaize ke liye bheji gayi dawaiyan:" : "Medications flagged for review:"}
            </span>
            <div className="space-y-3">
              {flaggedMedItems.map((item, idx) => {
                const isHigh = item.desc.severity === "high";
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-2xl border-2 transition-all ${
                      isHigh
                        ? "bg-red-50/90 border-emergencyRed-500 shadow-xs ring-1 ring-emergencyRed-400"
                        : "bg-amber-50/80 border-amber-300"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <Pill className={`w-4 h-4 ${isHigh ? "text-emergencyRed-700" : "text-amber-800"}`} />
                        <span className="font-bold text-sm text-navy-900">{item.desc.title}</span>
                      </div>
                      <span
                        className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          isHigh
                            ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300 font-extrabold"
                            : "bg-amber-100 text-amber-900 border border-amber-300"
                        }`}
                      >
                        {isHigh ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-emergencyRed-700" />
                        ) : (
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-700" />
                        )}
                        <span>{item.desc.severity.toUpperCase()} SEVERITY</span>
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs py-1">
                      <div className="p-2.5 rounded-xl bg-white/90 border border-slate-200">
                        <span className="text-slate-500 font-semibold block">{item.desc.recordText}</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-white/90 border border-slate-200">
                        <span className="text-navy-900 font-bold block">{item.desc.todayText}</span>
                      </div>
                    </div>

                    <div className="pt-2 flex items-center justify-between text-xs">
                      <p className={`font-semibold ${isHigh ? "text-emergencyRed-950 font-bold" : "text-amber-950"}`}>
                        {item.desc.reason}
                      </p>
                      <span className="text-[11px] font-bold text-slate-500 shrink-0 ml-2">
                        Needs clinician review
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Low Confidence Tag */}
        {checkIn.lowConfidence && (
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-300/80 flex items-start gap-2.5 text-xs text-slate-700 animate-fadeIn">
            <HelpCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <span className="font-medium leading-relaxed">
              {t.unansweredQuestionTag}
            </span>
          </div>
        )}

        {/* Mandatory Caption in Mock Mode only */}
        {!isLiveMode && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3 text-xs text-slate-600 leading-relaxed">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <span>{t.conflictSimulationCaption}</span>
          </div>
        )}

        {/* Continue to Routed to Review */}
        <button
          type="button"
          onClick={() => setScreen("conflict_review")}
          id="conflict-continue-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <span>{t.continue}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>
    </div>
  );
};
