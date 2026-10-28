import type { Metadata, Viewport } from "next";
import { Providers, themeBootScript } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ProjectForge AI", template: "%s · ProjectForge AI" },
  description: "AI-native project management operating system with explainable health and governed agents.",
  applicationName: "ProjectForge AI",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#07061a" },
    { media: "(prefers-color-scheme: light)", color: "#f6f5fb" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
      </head>
      <body className="font-sans text-fg">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
