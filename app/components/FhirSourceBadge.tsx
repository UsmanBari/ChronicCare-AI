import React from "react";
import { Database } from "lucide-react";

export const FhirSourceBadge = () => (
  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-teal-50 border border-teal-200 text-[9px] font-bold uppercase tracking-wide text-teal-700">
    <Database className="w-2.5 h-2.5" />
    FHIR
  </span>
);
