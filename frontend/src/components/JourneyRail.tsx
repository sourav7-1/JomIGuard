"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { strings } from "@/lib/strings";

const items = [
  { label: "মূল পাতা", mobile: "হোম", href: "/", match: (p: string) => p === "/", icon: "m3 11 9-8 9 8 M5.5 10v10h13V10 M9.5 20v-6h5v6" },
  { label: "কাগজ যাচাই", mobile: "যাচাই", href: "/cases", match: (p: string) => (p.startsWith("/cases") && !p.includes("/timeline")) || p.startsWith("/upload"), icon: "M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6" },
  { label: "জমির ইতিহাস", mobile: "ইতিহাস", desktopOnly: true, href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline", match: (p: string) => p.includes("/timeline"), icon: "M4 6h12 M12 2l4 4-4 4 M20 18H8 M12 14l-4 4 4 4" },
  { label: strings.nav.chat, mobile: "সহায়ক", href: "/chat", match: (p: string) => p.startsWith("/chat"), icon: "M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-5 4v-4.3A2.5 2.5 0 0 1 4 13.5z" },
  { label: "বায়না escrow", mobile: "বায়না", desktopOnly: true, href: "/escrow", match: (p: string) => p.startsWith("/escrow"), icon: "M3 8h18v11H3z M3 11h18 M7 15h4 M7 4h10" },
  { label: "প্রবাসী গার্ডিয়ান", mobile: "গার্ডিয়ান", href: "/guardian", match: (p: string) => p.startsWith("/guardian"), icon: "M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6z M9 11.5l2 2 4-4" },
  { label: strings.identity.profile, mobile: strings.identity.profileShort, href: "/profile", match: (p: string) => p.startsWith("/profile"), icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21a8 8 0 0 1 16 0" },
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
              <span className="truncate"> <span className="md:hidden">{item.mobile}</span><span className="hidden md:inline">{item.label}</span></span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
