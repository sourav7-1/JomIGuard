"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { strings } from "@/lib/strings";

const SERVICE_ROUTES = ["/cases", "/upload", "/find", "/escrow", "/guardian"];
const items = [
  { label: "সেবাসমূহ", en: "Services", mobile: "সেবা", href: "/", match: (p: string) => p === "/" || SERVICE_ROUTES.some((r) => p.startsWith(r)), icon: "m3 11 9-8 9 8 M5.5 10v10h13V10 M9.5 20v-6h5v6" },
  { label: "নমুনা ডেটা", en: "Demo data", mobile: "নমুনা", href: "/demo", match: (p: string) => p.startsWith("/demo"), icon: "M4 7h16v12H4z M8 7V4h8v3 M9 12h6 M9 15.5h4" },
  { label: "কীভাবে কাজ করে", en: "How it works", mobile: "কীভাবে", href: "/how-it-works", match: (p: string) => p.startsWith("/how-it-works"), icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 8v5 M12 16.5v.01" },
  { label: "ডকস", en: "Docs", mobile: "ডকস", href: "/docs", match: (p: string) => p.startsWith("/docs"), icon: "M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6" },
  { label: "সাহায্য", en: "Help", mobile: "সাহায্য", href: "/help", match: (p: string) => p.startsWith("/help"), icon: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6 M12 17h.01" },
  { label: strings.nav.chat, en: "AI assistant", desktopOnly: true, mobile: "সহায়ক", href: "/chat", match: (p: string) => p.startsWith("/chat"), icon: "M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-5 4v-4.3A2.5 2.5 0 0 1 4 13.5z" },
  { label: strings.identity.profile, en: "Profile", desktopOnly: true, mobile: strings.identity.profileShort, href: "/profile", match: (p: string) => p.startsWith("/profile"), icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21a8 8 0 0 1 16 0" },
];

function NavIcon({ path }: { path: string }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-[19px] w-[19px] shrink-0"><path d={path} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export function JourneyRail() {
  const pathname = usePathname();

  return (
    <nav aria-label="প্রধান নেভিগেশন" className="mobile-dock md:static md:mx-auto md:max-w-7xl md:px-8 md:pb-0">
      <div className="flex items-stretch justify-around border-t border-line bg-surface/95 px-1 pt-1 backdrop-blur-md md:justify-start md:gap-2 md:border-0 md:border-t md:bg-transparent md:p-0">
        {items.map((item) => {
          const active = item.match(pathname);
          return (
            <Link
              key={item.href + item.label}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent md:min-h-12 md:flex-row md:flex-none md:gap-2 md:rounded-none md:border-b-2 md:px-3 md:text-sm ${"desktopOnly" in item ? "hidden md:flex" : ""} ${active ? "bg-accent-soft text-accent md:border-gold md:bg-transparent" : "border-transparent text-muted hover:bg-surface hover:text-ink md:hover:bg-transparent"}`}
            >
              <NavIcon path={item.icon} />
              <span className="truncate"> <span className="md:hidden">{item.mobile}</span><span className="hidden md:inline">{item.label}<span lang="en" className="block text-[10px] font-normal leading-tight opacity-70">{item.en}</span></span></span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
