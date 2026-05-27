import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";
import { Providers } from "./providers";
import { ServiceWorkerRegister } from "@/components/system/service-worker-register";

export const metadata: Metadata = {
  title: { default: "Rain", template: "%s · Rain" },
  description: "AI workspace with chat personas, document RAG, and skill orchestration.",
  applicationName: "Rain",
  appleWebApp: {
    capable: true,
    title: "Rain",
    statusBarStyle: "black-translucent",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-ink-50 dark:bg-ink-950 text-ink-900 dark:text-ink-100 antialiased">
        <Providers>{children}</Providers>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}