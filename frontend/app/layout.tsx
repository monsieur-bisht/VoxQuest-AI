import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "VoxQuest-AI",
  description: "Voice-first interactive RPG and speech AI benchmark starter",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
