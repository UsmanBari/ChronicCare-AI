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
    const demoPatients = [
      "name@example.com",
      "ali.khan@demo.care",
      "patient@demo.care",
      "audit.patient@demo.care",
      "new.patient@demo.care",
      "demo_patient_htn@demo.care",
      "demo_patient_dm@demo.care",
      "demo_patient_dual@demo.care",
      "demo_patient_ur@demo.care",
      "demo_patient_roman_ur@demo.care",
      "demo_patient_emg@demo.care",
      "demo_patient_norx@demo.care",
      "demo_patient_fhir@demo.care",
      "demo_patient_new@demo.care",
    ];

    if (demoPatients.includes(normalized)) {
      return "patient";
    }

    const demoProviders = [
      "name.provider@example.com",
      "dr.sanamalik@citygeneral.org",
      "provider@demo.care",
      "provider.demo@demo.care",
    ];

    if (demoProviders.includes(normalized)) {
      return "provider";
    }

    const demoAdmins = [
      "usman@gmail.com",
      "admin@citygeneral.org",
      "admin@demo.care",
      "admin.demo@demo.care",
    ];

    if (demoAdmins.includes(normalized)) {
      return "admin";
    }
  }

  return null;
}

