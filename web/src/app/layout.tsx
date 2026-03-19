import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ui/ThemeProvider";

export const metadata: Metadata = {
  title: {
    default: "RAG Smart QA — Intelligent Document Intelligence",
    template: "%s | RAG Smart QA",
  },
  description:
    "Upload documents. Ask questions. Get precise answers with cited sources. RAG Smart QA brings AI-powered document intelligence to your workflow.",
  keywords: ["document AI", "RAG", "question answering", "document search", "AI"],
  openGraph: {
    title: "RAG Smart QA — Intelligent Document Intelligence",
    description: "Upload documents. Ask questions. Get precise answers with cited sources.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
