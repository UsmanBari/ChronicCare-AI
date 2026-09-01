"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Plus, Trash2, ArrowRight, Activity, Pill, User } from "lucide-react";

export const HealthProfileScreen = () => {
  const { setScreen, profile, setProfile, t, isUrdu } = useApp();

  const [conditions, setConditions] = useState<string[]>(profile.conditions || ["Type 2 Diabetes"]);
  const [medications, setMedications] = useState<string[]>(
    profile.medications.length > 0 ? profile.medications : ["Metformin 500mg"]
  );
  const [age, setAge] = useState<string>(profile.age || "58");

  const handleConditionToggle = (conditionValue: "t2d" | "htn" | "both") => {
    if (conditionValue === "both") {
      setConditions(["Type 2 Diabetes", "Hypertension"]);
    } else if (conditionValue === "t2d") {
      if (conditions.includes("Type 2 Diabetes") && conditions.length > 1) {
        setConditions(conditions.filter((c) => c !== "Type 2 Diabetes"));
      } else {
        setConditions([...conditions.filter((c) => c !== "Type 2 Diabetes"), "Type 2 Diabetes"]);
      }
    } else if (conditionValue === "htn") {
      if (conditions.includes("Hypertension") && conditions.length > 1) {
        setConditions(conditions.filter((c) => c !== "Hypertension"));
      } else {
        setConditions([...conditions.filter((c) => c !== "Hypertension"), "Hypertension"]);
      }
    }
  };

  const handleAddMedication = () => {
    setMedications([...medications, ""]);
  };

  const handleMedChange = (index: number, value: string) => {
    const updated = [...medications];
    updated[index] = value;
    setMedications(updated);
  };

  const handleRemoveMedication = (index: number) => {
    if (medications.length <= 1) {
      setMedications([""]);
      return;
    }
    setMedications(medications.filter((_, i) => i !== index));
  };

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanMeds = medications.filter((m) => m.trim().length > 0);
    setProfile({
      conditions: conditions.length > 0 ? conditions : ["Type 2 Diabetes"],
      medications: cleanMeds.length > 0 ? cleanMeds : ["Metformin 500mg"],
      age: age || "58",
    });
    setScreen("home");
  };

  const hasT2D = conditions.includes("Type 2 Diabetes");
  const hasHTN = conditions.includes("Hypertension");
  const hasBoth = hasT2D && hasHTN;

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Header */}
      <div className="bg-navy-800 p-6 text-white text-center">
        <h1 className="font-heading text-2xl font-bold mb-1">{t.profileTitle}</h1>
        <p className="text-xs text-slate-300 max-w-md mx-auto">{t.profileSubtitle}</p>
      </div>

      <form onSubmit={handleContinue} className="p-6 space-y-6">
        {/* Conditions selection */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-3 flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.conditionsLabel}</span>
          </label>
          <div className="space-y-2.5">
            {/* Type 2 Diabetes */}
            <label className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-t2d"
                checked={hasT2D}
                onChange={() => handleConditionToggle("t2d")}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">{t.type2Diabetes}</span>
            </label>

            {/* Hypertension */}
            <label className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-htn"
                checked={hasHTN}
                onChange={() => handleConditionToggle("htn")}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">{t.hypertension}</span>
            </label>

            {/* Both shortcut */}
            <label className="flex items-center gap-3 p-3 rounded-xl border border-teal-200 bg-teal-50/50 hover:bg-teal-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-both"
                checked={hasBoth}
                onChange={() => handleConditionToggle("both")}
                className="w-4 h-4 text-teal-700 rounded border-teal-300 focus:ring-teal-700"
              />
              <span className="text-sm font-semibold text-teal-900">{t.bothConditions}</span>
            </label>
          </div>
        </div>

        {/* Current Medications */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Pill className="w-4 h-4 text-teal-700" />
              <span>{t.medicationsLabel}</span>
            </label>
            <button
              type="button"
              onClick={handleAddMedication}
              id="add-med-btn"
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 transition-colors"
            >
              {t.addMedication}
            </button>
          </div>
          <p className="text-[11px] text-slate-500 mb-2.5">{t.medicationsHint}</p>

          <div className="space-y-2">
            {medications.map((med, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <input
                  type="text"
                  value={med}
                  id={`medication-input-${idx}`}
                  onChange={(e) => handleMedChange(idx, e.target.value)}
                  placeholder={t.medicationPlaceholder}
                  className="flex-1 text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
                />
                {medications.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveMedication(idx)}
                    title={t.removeMedication}
                    className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Age */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-1.5 flex items-center gap-1.5" htmlFor="patient-age">
            <User className="w-4 h-4 text-teal-700" />
            <span>{t.ageLabel}</span>
          </label>
          <input
            id="patient-age"
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder={t.agePlaceholder}
            className="w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
          />
        </div>

        {/* Continue Button */}
        <button
          type="submit"
          id="profile-continue-btn"
          className="w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <span>{t.continue}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </form>
    </div>
  );
};
