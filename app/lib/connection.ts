import { EHRConnectionResponse } from "./api";

export type ConnectionMode = "fhir" | "offline";

/**
 * Single source of truth for whether the current state is managed by a hospital EHR.
 * In live mode: managed iff liveEhrConnection?.mode is "fhir" or "connected".
 * In non-live demo mode: managed iff connectionMode is "fhir".
 */
export function isEhrManaged(
  isLiveMode: boolean,
  connectionMode?: ConnectionMode | string | null,
  liveEhrConnection?: EHRConnectionResponse | null
): boolean {
  if (isLiveMode) {
    const mode = liveEhrConnection?.mode;
    return mode === "fhir" || mode === "connected";
  }
  return connectionMode === "fhir";
}
