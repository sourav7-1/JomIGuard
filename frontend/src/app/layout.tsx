import type { Metadata } from "next";
import { Suspense } from "react";
import { Hind_Siliguri, IBM_Plex_Mono, Tiro_Bangla } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { strings } from "@/lib/strings";
import { AuthGuard } from "@/components/AuthGuard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ToastProvider } from "@/components/ui/Toast";

const tiroBangla = Tiro_Bangla({
  weight: "400",
  subsets: ["bengali"],
  variable: "--font-tiro-bangla",
  display: "swap",
});

const hindSiliguri = Hind_Siliguri({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["bengali"],
  variable: "--font-hind-siliguri",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-ibm-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: `${strings.app.name} — ${strings.app.taglineShort}`,
  description: strings.app.tagline,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="bn"
      className={`${tiroBangla.variable} ${hindSiliguri.variable} ${ibmPlexMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-bg text-ink selection:bg-accent-soft selection:text-accent">
        <ToastProvider>
        <Header />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-7 pb-24 sm:px-6 md:py-10 md:pb-10 lg:px-8">
          <Suspense fallback={<div role="status" aria-label="লোড হচ্ছে" className="space-y-4"><Skeleton className="h-9 w-72 max-w-full" /><Skeleton className="h-40 w-full !rounded-[var(--radius-card)]" /></div>}>
            <AuthGuard>{children}</AuthGuard>
          </Suspense>
        </main>
        <footer className="w-full border-t border-line bg-surface/50 mt-auto py-6">
          <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 pb-24 text-sm text-muted sm:px-6 md:flex-row md:items-start md:justify-between md:pb-6 lg:px-8">
            <p className="max-w-3xl leading-relaxed">
              {strings.app.disclaimer}
            </p>
            <div className="shrink-0 md:text-right">
              <p className="font-medium text-ink">{strings.app.footerText}</p>
              <p className="mt-1">{strings.app.independentNote}</p>
              <p className="mt-1">Developed by Team 2:29 AM Error</p>
            </div>
          </div>
        </footer>
        </ToastProvider>
      </body>
    </html>
  );
}
