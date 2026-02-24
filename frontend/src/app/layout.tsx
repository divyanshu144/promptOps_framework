import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PromptOps Dashboard",
  description: "Prompt-as-code optimization and evaluation dashboard.",
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
