import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WuWa AI Coach",
  description: "Unofficial Wuthering Waves account and echo coaching tool",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
