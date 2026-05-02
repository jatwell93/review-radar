import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Review Radar",
  description: "Actionable insights from your Google reviews",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-800`}>
        <nav className="bg-slate-800 px-6 py-4 flex items-center justify-between">
          <span className="text-white font-semibold text-lg">Review Radar</span>
          <span className="text-sm text-slate-400">Part of Pharm IQ</span>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
