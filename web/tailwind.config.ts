import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        canvas: "#f5f7fb",
        accent: "#0f766e",
        sand: "#f8fafc"
      },
      boxShadow: {
        panel: "0 10px 30px rgba(15, 23, 42, 0.08)"
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(circle at top left, rgba(15,118,110,0.20), transparent 35%), radial-gradient(circle at bottom right, rgba(59,130,246,0.16), transparent 30%)"
      }
    }
  },
  plugins: []
};

export default config;
