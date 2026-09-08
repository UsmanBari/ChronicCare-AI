"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity } from "lucide-react";

export const Preloader = ({ onComplete }: { onComplete: () => void }) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const duration = 1500;
    const start = Date.now();
    let frameId: number;

    const tick = () => {
      const elapsed = Date.now() - start;
      const pct = Math.min(100, Math.round((elapsed / duration) * 100));
      setProgress(pct);
      if (pct < 100) {
        frameId = requestAnimationFrame(tick);
      } else {
        setTimeout(onComplete, 300);
      }
    };

    frameId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-navy-900 select-none"
    >
      <motion.div
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        className="w-20 h-20 rounded-2xl bg-navy-800 border border-teal-500/30 flex items-center justify-center mb-5 shadow-xl shadow-teal-950/40"
      >
        <Activity className="w-10 h-10 text-teal-400" />
      </motion.div>

      <h1 className="font-heading text-2xl font-bold tracking-tight text-white mb-6">
        ChronicCare AI
      </h1>

      <div className="w-60 h-1 rounded-full bg-navy-800 overflow-hidden border border-navy-700/60 shadow-inner">
        <motion.div
          className="h-full bg-teal-400 rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      <span className="mt-2.5 text-xs font-mono text-slate-400 tabular-nums">
        {progress}%
      </span>

      <span className="mt-4 text-[11px] uppercase tracking-widest text-teal-400/60 font-medium">
        Clinical Continuity Engine
      </span>
    </motion.div>
  );
};
