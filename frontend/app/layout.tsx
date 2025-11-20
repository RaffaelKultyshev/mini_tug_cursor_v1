import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mini-TUG Control Center",
  description: "AI-Based ERP for your startup",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

