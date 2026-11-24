"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Card, IconTile } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { ServiceIcon } from "@/components/ServiceIcon";
import { Service, services } from "@/lib/services";
import { useLang } from "@/lib/lang";

/** Home "সেবাসমূহ" grid: whole card opens the service, "কীভাবে?" opens its guide in a modal. */
export function ServiceGrid() {
  const [help, setHelp] = useState<Service | null>(null);
  const en = useLang() === "en";
  const label = (s: Service) => (en ? s.start.labelEn : s.start.label);
  return (
    <>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {services.map((s, i) => (
          <Card
            key={s.id}
            as="li"
            variant="interactive"
            href={s.start.href}
            className={`animate-fade-up flex flex-col ${s.satellite ? "!border-sat/35 hover:!border-sat/60" : ""}`}
            style={{ "--i": i } as React.CSSProperties}
            icon={<IconTile satellite={s.satellite}><ServiceIcon path={s.icon} /></IconTile>}
            title={en ? s.titleEn : s.title}
            description={en ? s.lineEn : s.line}
            footer={<>
              <span aria-hidden="true" className={`inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] px-4 text-sm font-semibold text-white shadow-rest ${s.satellite ? "bg-sat" : "bg-accent"}`}>
                {label(s)} <span>→</span>
              </span>
              <button type="button" onClick={() => setHelp(s)} className="inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line bg-surface px-3 text-sm font-semibold text-accent hover:bg-accent-soft">
                {en ? "How?" : "কীভাবে?"}<span className="sr-only"> {en ? `steps for ${s.titleEn}` : `${s.title} ব্যবহারের ধাপ`}</span>
              </button>
            </>}
          />
        ))}
      </ul>
      <Modal
        open={!!help}
        onClose={() => setHelp(null)}
        title={help ? (en ? `${help.titleEn}: how to use it` : `${help.title}: কীভাবে ব্যবহার করবেন`) : ""}
        description={en ? help?.lineEn : help?.line}
        footer={help && <Link href={help.start.href} className="inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{label(help)} →</Link>}
      >
        <ol className="space-y-3">
          {(en ? help?.howToEn : help?.howTo)?.map((step, i) => (
            <li key={step} className="flex gap-3 text-sm leading-7 text-ink">
              <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-bold text-accent">{en ? i + 1 : "১২৩৪৫"[i]}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </Modal>
    </>
  );
}
