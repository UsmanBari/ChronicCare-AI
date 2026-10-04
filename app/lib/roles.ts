export type UserRole = "patient" | "provider" | "admin";

/**
 * Maps an email address to a user role based on environment configuration.
 * Returns null if the email is not mapped to any known role.
 */
export function getRoleFromEmail(email: string): UserRole | null {
  if (!email) return null;
  const normalized = email.trim().toLowerCase();

  const patientEmail = (
    process.env.NEXT_PUBLIC_DEMO_PATIENT_EMAIL || "saad@gmail.com"
  ).trim().toLowerCase();
  const providerEmail = (
    process.env.NEXT_PUBLIC_DEMO_PROVIDER_EMAIL || "hassaan@gmail.com"
  ).trim().toLowerCase();
  const adminEmail = (
    process.env.NEXT_PUBLIC_DEMO_ADMIN_EMAIL || "usman@gmail.com"
  ).trim().toLowerCase();

  if (normalized === patientEmail) {
    return "patient";
  }
  if (normalized === providerEmail) {
    return "provider";
  }
  if (normalized === adminEmail) {
    return "admin";
  }

  return null;
}
