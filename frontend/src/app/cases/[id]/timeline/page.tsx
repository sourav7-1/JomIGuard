"use client";

import React, { Suspense } from "react";
import { useParams } from "next/navigation";
import { OwnershipTimeline } from "@/components/case/OwnershipTimeline";

function TimelineRoute() {
  const { id } = useParams<{ id: string }>();
  return <OwnershipTimeline id={id} />;
}

export default function CaseTimelinePage() {
  return <Suspense fallback={null}><TimelineRoute /></Suspense>;
}
