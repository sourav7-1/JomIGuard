"use client";

import React, { useState } from "react";
import {
  Button,
  Card,
  Box,
  Badge,
  StatusPill,
  CheckItem,
  VerdictBox,
  Checklist,
  Spinner,
  EmptyState,
  ErrorState,
  type DocumentStatus,
} from "@/components/ui";
import { strings } from "@/lib/strings";

function ComponentShowcase({ themeName }: { themeName: string }) {
  const [checklist, setChecklist] = useState([
    { id: "1", label: strings.checklist.demoItem1, checked: false },
    { id: "2", label: strings.checklist.demoItem2, checked: true },
    { id: "3", label: strings.checklist.demoItem3, checked: false },
  ]);

  const toggleCheck = (id: string, checked: boolean) => {
    setChecklist((prev) =>
      prev.map((item) => (item.id === id ? { ...item, checked } : item))
    );
  };

  const statuses: DocumentStatus[] = [
    "uploaded",
    "queued",
    "processing",
    "done",
    "failed",
    "needs_review",
  ];

  return (
    <div className="space-y-6 max-w-full overflow-hidden">
      <div className="border-b border-line pb-2 flex items-center justify-between gap-2">
        <h2 className="text-lg font-bold font-heading text-ink">{themeName}</h2>
        <Badge variant="ok">{strings.labels.allComponentsReady}</Badge>
      </div>

      {/* Buttons */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">Button (Primary, Ghost, Disabled)</h3>
        <div className="flex flex-wrap gap-2.5 items-center">
          <Button variant="primary">{strings.buttons.upload}</Button>
          <Button variant="ghost">{strings.buttons.next}</Button>
          <Button variant="primary" disabled>
            {strings.buttons.submit}
          </Button>
          <Button variant="ghost" size="sm">
            {strings.buttons.back}
          </Button>
        </div>
      </section>

      {/* Badges */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">Badge (ok, warn, bad, neutral)</h3>
        <div className="flex flex-wrap gap-2 items-center">
          <Badge variant="ok">✓ {strings.status.ok}</Badge>
          <Badge variant="warn">? {strings.status.warn}</Badge>
          <Badge variant="bad">! {strings.status.bad}</Badge>
          <Badge variant="neutral">{strings.status.neutral}</Badge>
        </div>
      </section>

      {/* StatusPills */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">StatusPill (Document Status)</h3>
        <div className="flex flex-wrap gap-2 items-center">
          {statuses.map((s) => (
            <StatusPill key={s} status={s} />
          ))}
        </div>
      </section>

      {/* Cards & Box */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">Card / Box</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Card variant="surface">
            <h4 className="text-sm font-bold font-heading text-ink mb-1">Surface Card</h4>
            <p className="text-xs text-muted leading-relaxed">
              নথি ও তথ্যের প্রধান কার্ড ব্যাকগ্রাউন্ড।
            </p>
          </Card>
          <Box variant="soft">
            <h4 className="text-sm font-bold font-heading text-accent mb-1">Soft Box</h4>
            <p className="text-xs text-ink leading-relaxed">
              হালকা হাইলাইট ও অতিরিক্ত তথ্য দেখানোর জন্য।
            </p>
          </Box>
        </div>
      </section>

      {/* VerdictBox */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">VerdictBox (Risk Levels)</h3>
        <div className="space-y-3">
          <VerdictBox riskLevel="low" />
          <VerdictBox riskLevel="medium" />
          <VerdictBox riskLevel="high" />
          <VerdictBox riskLevel="unknown" />
        </div>
      </section>

      {/* CheckItem */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">CheckItem (✓ ! ? rows like demo)</h3>
        <div className="space-y-2.5">
          <CheckItem
            status="ok"
            description={strings.checkItem.sampleMatch}
            sources={["খতিয়ান BS ৮৮২", "বিক্রয় দলিল"]}
          />
          <CheckItem
            status="bad"
            title={strings.checkItem.mismatchTitle}
            description={strings.checkItem.sampleMismatch}
            sources={["খতিয়ান অংশ ৬%", "দলিল ১০%"]}
          />
          <CheckItem
            status="warn"
            title={strings.checkItem.consentTitle}
            description={strings.checkItem.sampleConsent}
          />
        </div>
      </section>

      {/* Checklist */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">Checklist</h3>
        <Card variant="surface" className="p-3 sm:p-4">
          <Checklist items={checklist} onToggle={toggleCheck} />
        </Card>
      </section>

      {/* Spinner */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">Spinner</h3>
        <div className="flex items-center gap-4">
          <Spinner size="sm" />
          <Spinner size="md" />
          <Spinner size="lg" />
        </div>
      </section>

      {/* EmptyState */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">EmptyState</h3>
        <EmptyState
          title={strings.empty.noDocumentsTitle}
          description={strings.empty.noDocumentsDesc}
          actionLabel={strings.buttons.upload}
        />
      </section>

      {/* ErrorState */}
      <section className="space-y-2.5">
        <h3 className="text-sm font-semibold text-muted">ErrorState</h3>
        <ErrorState
          title={strings.error.defaultTitle}
          message={strings.error.defaultMessage}
          onRetry={() => {}}
        />
      </section>
    </div>
  );
}

export default function DevComponentsPage() {
  const [activeTab, setActiveTab] = useState<"both" | "light" | "dark">("both");

  return (
    <div className="space-y-6 max-w-full py-4 overflow-x-hidden">
      <div className="space-y-2">
        <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
          {strings.pages.devComponents.title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.devComponents.desc}
        </p>

        {/* Tab switcher */}
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={() => setActiveTab("both")}
            className={`min-h-[44px] px-3.5 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              activeTab === "both"
                ? "bg-accent text-white border-accent"
                : "bg-surface text-ink border-line"
            }`}
          >
            উভয় থিম
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("light")}
            className={`min-h-[44px] px-3.5 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              activeTab === "light"
                ? "bg-accent text-white border-accent"
                : "bg-surface text-ink border-line"
            }`}
          >
            {strings.pages.devComponents.lightSection}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("dark")}
            className={`min-h-[44px] px-3.5 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              activeTab === "dark"
                ? "bg-accent text-white border-accent"
                : "bg-surface text-ink border-line"
            }`}
          >
            {strings.pages.devComponents.darkSection}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-full">
        {(activeTab === "both" || activeTab === "light") && (
          <div
            data-theme="light"
            className="p-4 sm:p-6 rounded-2xl bg-bg text-ink border border-line shadow-xs space-y-6 overflow-hidden max-w-full"
          >
            <ComponentShowcase themeName={strings.pages.devComponents.lightSection} />
          </div>
        )}

        {(activeTab === "both" || activeTab === "dark") && (
          <div
            data-theme="dark"
            className="p-4 sm:p-6 rounded-2xl bg-bg text-ink border border-line shadow-xs space-y-6 overflow-hidden max-w-full"
          >
            <ComponentShowcase themeName={strings.pages.devComponents.darkSection} />
          </div>
        )}
      </div>
    </div>
  );
}
