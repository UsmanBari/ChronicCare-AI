"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { AlertCircle } from "lucide-react";

export const DemoFooter = () => {
  const { t, isLiveMode } = useApp();

  return (
    <footer className="mt-8 pt-6 pb-8 border-t border-slate-200 text-center text-xs text-slate-500">
      <div className="max-w-md mx-auto px-4 space-y-2">
        {isLiveMode ? (
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-[11px]">
            <AlertCircle className="w-3.5 h-3.5 text-slate-600" />
            <span>{t.researchPrototypeNotice}</span>
          </div>
        ) : (
          <>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 font-semibold tracking-wider text-[11px] uppercase">
              <AlertCircle className="w-3.5 h-3.5 text-amber-800" />
              <span>{t.demoWatermark}</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              {t.disclaimerScope}
            </p>
          </>
        )}
      </div>
    </footer>
  );
};
