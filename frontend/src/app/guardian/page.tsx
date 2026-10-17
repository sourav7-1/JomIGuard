import React from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { strings } from "@/lib/strings";

export default function GuardianPage() {
  return (
    <div className="space-y-6 max-w-3xl mx-auto py-4">
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
          {strings.pages.guardian.title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.guardian.desc}
        </p>
      </div>

      <Card className="space-y-3 border-warn/40 bg-warn-bg/20">
        <div className="flex items-center justify-between gap-2">
          <span className="font-bold text-sm text-warn">
            ⚠️ {strings.pages.guardian.alertSampleTitle}
          </span>
          <Badge variant="warn">পরিবর্তন শনাক্ত</Badge>
        </div>
        <p className="text-sm text-ink leading-relaxed">
          {strings.pages.guardian.alertSampleDesc}
        </p>
      </Card>
    </div>
  );
}
