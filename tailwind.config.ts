import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0F182A",
          800: "#16233F", // Primary Deep Navy
          700: "#1E3056",
          600: "#2B4374",
          100: "#E9EDF5",
          50: "#F4F6FA",
        },
        teal: {
          900: "#063A3C",
          800: "#085355",
          700: "#0B6E70", // Accent Teal
          600: "#108B8D",
          500: "#17A2A5",
          100: "#E2F4F4",
          50: "#F0F9F9",
        },
        amber: {
          800: "#8A5A18", // Supporting Amber
          700: "#A36B1E",
          100: "#FDF5E8",
          50: "#FEFAF3",
        },
        mutedGreen: {
          800: "#24623F", // Supporting Muted Green
          700: "#2E7C50",
          100: "#EAF5EF",
          50: "#F4FAF6",
        },
        emergencyRed: {
          800: "#B0362C", // Reserved strictly for emergencies
          700: "#C93E33",
          100: "#FBEAE8",
          50: "#FCF5F4",
        },
      },
      fontFamily: {
        serif: ["Cambria", "Georgia", "serif"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        urdu: ["Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", "Urdu Typesetting", "Tahoma", "sans-serif"],
      },
      animation: {
        pulseFast: "pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        fadeIn: "fadeIn 0.35s ease-in-out",
        slideUp: "slideUp 0.35s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
