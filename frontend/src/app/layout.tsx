import type { Metadata } from "next";
import { Suspense } from "react";
import { Hind_Siliguri, IBM_Plex_Mono, Tiro_Bangla } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { strings } from "@/lib/strings";
import { AuthGuard } from "@/components/AuthGuard";
import { Spinner } from "@/components/ui/Spinner";

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
        <Header />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-7 pb-24 sm:px-6 md:py-10 md:pb-10 lg:px-8">
          <Suspense fallback={<div className="flex min-h-[50vh] items-center justify-center"><Spinner /></div>}>
            <AuthGuard>{children}</AuthGuard>
          </Suspense>
        </main>
        <footer className="w-full border-t border-line bg-surface/50 mt-auto py-6">
          <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 pb-20 text-xs text-muted sm:px-6 md:flex-row md:items-start md:justify-between md:pb-6 lg:px-8">
            <p className="max-w-3xl leading-relaxed">
              {strings.app.disclaimer}
            </p>
            <div className="shrink-0 text-right">
              <p className="font-medium text-ink">{strings.app.footerText}</p>
              <p className="mt-1">Developed by Team TerraByte</p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
