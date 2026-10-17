import React, { Suspense } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { strings } from "@/lib/strings";

const timelineEvents = [
  {
    year: "১৯৬২",
    title: "আব্দুল করিম, ১৫ শতাংশ",
    desc: "CS খতিয়ান। প্রথম রেকর্ড করা মালিক।",
    statusVariant: "ok" as const,
  },
  {
    year: "১৯৮৫",
    title: "বিক্রয়: আব্দুল করিম → রহমান, ১৫ শতাংশ",
    desc: "বায়া দলিল ১৯৮৫। SA খতিয়ান ২১৪-তে রহমানের নাম উঠেছে।",
    statusVariant: "ok" as const,
  },
  {
    year: "২০০৯",
    title: "রহমান মারা যান, ৩ জন ওয়ারিশ",
    desc: "রহিম (৬), করিম (৬), সালমা (৩) = মোট ১৫ শতাংশ।",
    statusVariant: "ok" as const,
  },
  {
    year: "২০২৬",
    title: "প্রস্তাবিত বিক্রি: রহিম → রফিক, ১০ শতাংশ",
    desc: "রহিমের অংশ ৬ শতাংশ। বাকি ৪ শতাংশ কোথা থেকে আসছে কাগজ নেই।",
    statusVariant: "bad" as const,
  },
];

async function TimelineContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="space-y-6 max-w-3xl mx-auto py-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
            {strings.pages.caseTimeline.title}
          </h1>
          <p className="text-sm text-muted leading-relaxed">
            {strings.pages.caseTimeline.desc}
          </p>
        </div>
        <Link
          href={`/cases/${id}`}
          className="min-h-[44px] px-3.5 py-2 rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center text-sm font-medium self-start sm:self-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          ← {strings.pages.caseTimeline.backToCase}
        </Link>
      </div>

      <div className="relative border-l-2 border-line ml-4 pl-6 space-y-6 my-6">
        {timelineEvents.map((ev, idx) => (
          <div key={idx} className="relative group">
            <div
              className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 bg-surface ${
                ev.statusVariant === "bad" ? "border-bad bg-bad-bg" : "border-ok bg-ok-bg"
              }`}
            />
            <Card className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-accent-soft text-accent">
                  {ev.year}
                </span>
              </div>
              <h3 className="text-sm md:text-base font-bold font-heading text-ink">
                {ev.title}
              </h3>
              <p className="text-xs md:text-sm text-muted leading-relaxed">
                {ev.desc}
              </p>
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CaseTimelinePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-12">
          <Spinner size="lg" />
        </div>
      }
    >
      <TimelineContent params={params} />
    </Suspense>
  );
}
