import type { Metadata } from "next";
import { Hind_Siliguri, IBM_Plex_Mono, Tiro_Bangla } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { strings } from "@/lib/strings";

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
        <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
          {children}
        </main>
        <footer className="w-full border-t border-line bg-surface/50 mt-auto py-6">
          <div className="max-w-5xl mx-auto px-4 text-center text-xs text-muted space-y-2">
            <p className="max-w-2xl mx-auto leading-relaxed">
              {strings.app.disclaimer}
            </p>
            <p className="font-medium text-ink">{strings.app.footerText}</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
