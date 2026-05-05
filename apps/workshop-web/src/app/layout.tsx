import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "Rain", template: "%s · Rain" },
  description: "Local AI Operating System",
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
      </body>
    </html>
  );
}