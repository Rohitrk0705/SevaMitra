import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SevaMithra — Autonomous Civic Welfare & RTI Escalation Agent",
  description:
    "Autonomous agent system for Indian citizens: discovers welfare schemes, verifies DigiLocker credentials, files applications, monitors SLA timelines, and drafts statutory Right to Information (RTI) petitions upon delay.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#05080a] text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
