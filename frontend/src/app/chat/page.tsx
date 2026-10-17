import React from "react";
import { Card } from "@/components/ui/Card";
import { strings } from "@/lib/strings";

export default function ChatPage() {
  return (
    <div className="space-y-6 max-w-2xl mx-auto py-4">
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
          {strings.pages.chat.title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.chat.desc}
        </p>
      </div>

      <Card className="p-8 text-center space-y-3">
        <div className="text-4xl">🤖</div>
        <h2 className="text-base font-bold font-heading text-ink">
          {strings.pages.chat.title}
        </h2>
        <p className="text-sm text-muted max-w-md mx-auto leading-relaxed">
          {strings.pages.chat.desc}
        </p>
      </Card>
    </div>
  );
}
