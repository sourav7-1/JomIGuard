import React from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { strings } from "@/lib/strings";

const sampleCases = [
  {
    id: "case-305",
    mouza: "চাঁদশী",
    dag: "৩০৫",
    khatian: "BS ৮৮২",
    status: "উচ্চ ঝুঁকি",
    statusVariant: "bad" as const,
    note: "খতিয়ানে রহিমের অংশ ৬ শতাংশ, দলিলে ১০ শতাংশ হস্তান্তর",
  },
];

export default function CasesPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto py-4">
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
          {strings.pages.cases.title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.cases.desc}
        </p>
      </div>

      <div className="space-y-3">
        {sampleCases.map((c) => (
          <Link
            key={c.id}
            href={`/cases/${c.id}`}
            className="block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded-xl"
          >
            <Card className="hover:border-accent/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base font-heading text-ink">
                    মৌজা {c.mouza}, দাগ {c.dag}
                  </span>
                  <Badge variant={c.statusVariant}>{c.status}</Badge>
                </div>
                <p className="text-xs text-muted">
                  খতিয়ান: {c.khatian} • {c.note}
                </p>
              </div>
              <span className="text-xs font-semibold text-accent self-end sm:self-center">
                {strings.buttons.viewDetails} →
              </span>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
