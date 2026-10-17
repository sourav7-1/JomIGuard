"use client";

import React, { useState, useRef } from "react";
import { strings } from "@/lib/strings";

interface DocumentImageViewerProps {
  fileUrl: string | null;
  filename: string;
}

export function DocumentImageViewer({ fileUrl, filename }: DocumentImageViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isOpen, setIsOpen] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);

  const isPdf = filename.toLowerCase().endsWith(".pdf");

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (isPdf) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || isPdf) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isPdf) return;
    setIsDragging(false);
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    if (isPdf) return;
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  };

  return (
    <div className="flex flex-col border border-line rounded-xl bg-surface overflow-hidden shadow-xs">
      <div className="flex items-center justify-between px-3 py-2 border-b border-line bg-bg/50">
        <span className="text-sm font-semibold font-heading text-ink flex items-center gap-1.5">
          📄 {strings.casePage.originalDocTitle}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden text-xs text-accent font-medium px-2 py-1 rounded min-h-[36px]"
          >
            {isOpen ? strings.casePage.toggleImageHide : strings.casePage.toggleImageShow}
          </button>

          {!isPdf && isOpen && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleZoomIn}
                title={strings.casePage.zoomIn}
                aria-label={strings.casePage.zoomIn}
                className="w-8 h-8 rounded border border-line bg-surface hover:bg-bg flex items-center justify-center text-sm font-bold text-ink"
              >
                +
              </button>
              <button
                type="button"
                onClick={handleZoomOut}
                title={strings.casePage.zoomOut}
                aria-label={strings.casePage.zoomOut}
                className="w-8 h-8 rounded border border-line bg-surface hover:bg-bg flex items-center justify-center text-sm font-bold text-ink"
              >
                -
              </button>
              <button
                type="button"
                onClick={handleReset}
                title={strings.casePage.zoomReset}
                aria-label={strings.casePage.zoomReset}
                className="px-2 h-8 rounded border border-line bg-surface hover:bg-bg text-xs font-medium text-muted"
              >
                {strings.casePage.zoomReset}
              </button>
            </div>
          )}
        </div>
      </div>

      {isOpen && (
        <div
          ref={containerRef}
          onWheel={handleWheel}
          className="relative w-full h-[360px] md:h-[500px] overflow-hidden bg-bg/20 flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
        >
          {!fileUrl ? (
            <div className="text-xs text-muted">ফাইল লোড হচ্ছে...</div>
          ) : isPdf ? (
            <iframe
              src={fileUrl}
              title={filename}
              className="w-full h-full border-0"
            />
          ) : (
            <div
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: "center center",
                touchAction: "none",
              }}
              className="transition-transform duration-75 ease-out max-w-full max-h-full flex items-center justify-center"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={fileUrl}
                alt={filename}
                className="max-h-[480px] w-auto object-contain pointer-events-none rounded shadow-sm"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
