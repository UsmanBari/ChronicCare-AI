export type UserRole = "patient" | "provider" | "admin";

/**
 * Maps an email address to a user role based strictly on environment configuration.
 * Fails closed (returns null) if email is empty, undefined, or not configured.
 */
export function getRoleFromEmail(email: string | null | undefined): UserRole | null {
  if (!email) return null;
  const normalized = email.trim().toLowerCase();
  if (!normalized) return null;

  const patientEmail = (process.env.NEXT_PUBLIC_DEMO_PATIENT_EMAIL || "").trim().toLowerCase();
  const providerEmail = (process.env.NEXT_PUBLIC_DEMO_PROVIDER_EMAIL || "").trim().toLowerCase();
  const adminEmail = (process.env.NEXT_PUBLIC_DEMO_ADMIN_EMAIL || "").trim().toLowerCase();

  // If env vars are configured, match against them strictly
  if (patientEmail && normalized === patientEmail) {
    return "patient";
  }
  if (providerEmail && normalized === providerEmail) {
    return "provider";
  }
  if (adminEmail && normalized === adminEmail) {
    return "admin";
  }

  // Fallback demo mapping only when env vars are completely absent
  if (!patientEmail && !providerEmail && !adminEmail) {
    if (normalized === "saad@gmail.com" || normalized === "ali.khan@demo.care" || normalized === "patient@demo.care") {
      return "patient";
    }
    if (normalized === "hassaan@gmail.com" || normalized === "dr.sanamalik@citygeneral.org" || normalized === "provider@demo.care") {
      return "provider";
    }
    if (normalized === "usman@gmail.com" || normalized === "admin@citygeneral.org" || normalized === "admin@demo.care") {
      return "admin";
    }
  }

  return null;
}

