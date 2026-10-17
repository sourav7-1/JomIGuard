import React from "react";
import { Card } from "@/components/ui/Card";
import { strings } from "@/lib/strings";

export default function EscrowPage() {
  return (
    <div className="space-y-6 max-w-3xl mx-auto py-4">
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
          {strings.pages.escrow.title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.escrow.desc}
        </p>
      </div>

      <Card className="space-y-4 p-6">
        <div className="p-4 rounded-lg bg-accent-soft text-accent text-xs md:text-sm font-medium leading-relaxed">
          {strings.pages.escrow.note}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-center">
          <div className="p-4 rounded-lg border border-line bg-surface">
            <div className="text-xs text-muted mb-1">ক্রেতা</div>
            <div className="font-bold text-base text-ink">রফিক সাহেব</div>
          </div>
          <div className="p-4 rounded-lg border-2 border-accent bg-accent-soft flex flex-col justify-center">
            <div className="text-xs font-bold text-accent mb-0.5">Escrow পার্টনার ব্যাংক</div>
            <div className="text-xs text-ink">শর্ত সাপেক্ষে বায়না জমা</div>
          </div>
          <div className="p-4 rounded-lg border border-line bg-surface">
            <div className="text-xs text-muted mb-1">বিক্রেতা</div>
            <div className="font-bold text-base text-ink">রহিম উদ্দিন</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
