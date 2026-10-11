import React from "react";
import Link from "next/link";
import { AlertCircle, Home, Shield } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50 text-navy-800">
      <div className="w-full max-w-md bg-white rounded-3xl border border-slate-200 p-8 shadow-xl text-center space-y-5 animate-fadeIn">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-800 shadow-sm">
          <AlertCircle className="w-8 h-8" />
        </div>

        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold uppercase tracking-wider mb-2">
            <Shield className="w-3.5 h-3.5" />
            404 • Prototype Navigation
          </span>
          <h1 className="font-heading text-2xl font-bold text-navy-800 tracking-tight">
            Page Not Found
          </h1>
          <p className="text-sm text-slate-600 mt-2 leading-relaxed">
            The requested page does not exist or has been moved.
          </p>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-500 italic">
          Research prototype, not a medical device.
        </div>

        <div className="pt-2">
          <Link
            href="/"
            id="not-found-return-home-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-4 h-4" />
            <span>Return to Home</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
