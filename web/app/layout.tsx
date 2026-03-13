import type { Metadata } from "next";
import { Manrope, IBM_Plex_Mono } from "next/font/google";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/app/providers";

import "./globals.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-sans" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "rag-smart-qa",
  description: "Advanced production-style RAG workspace"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${manrope.variable} ${mono.variable}`}>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
