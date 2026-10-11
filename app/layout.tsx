import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "./context/AppContext";
import { ErrorBoundary } from "./components/ErrorBoundary";

export const metadata: Metadata = {
  title: "ChronicCare AI — Clinical Continuity Engine (Research Prototype)",
  description: "Research prototype for proactive chronic condition monitoring and clinical reconciliation. Not a medical device.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-navy-800">
        <AppProvider>
          <ErrorBoundary>{children}</ErrorBoundary>
        </AppProvider>
      </body>
    </html>
  );
}
