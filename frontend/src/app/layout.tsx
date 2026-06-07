import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Prompt2Pixel",
  description: "Agentic AI Animation Studio powered by Manim and OpenAI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-screen bg-[#0a0a0a] text-white flex flex-col font-sans">
        {/* A simple glowing top border for that cyber feel */}
        <div className="h-1 w-full bg-gradient-to-r from-emerald-400 via-cyan-500 to-blue-500"></div>
        
        {children}
      </body>
    </html>
  );
}
