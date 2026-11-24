"use client";

import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import React, { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import { api, PlotGeometry } from "@/lib/api";
import { useLang } from "@/lib/lang";

const ESRI_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_ATTRIBUTION = "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community";
const DEFAULT_CENTER: [number, number] = [23.99, 90.41]; // Gazipur; the user pans to their plot
const DEFAULT_ZOOM = 15;

function drawLabels(L: typeof Leaflet, en: boolean) {
  const t = (b: string, e: string) => (en ? e : b);
  const d = L.drawLocal;
  d.draw.toolbar.buttons.polygon = t("প্লটের সীমানা আঁকুন", "Draw the plot boundary");
  d.draw.toolbar.actions = { title: t("আঁকা বাতিল করুন", "Cancel drawing"), text: t("বাতিল", "Cancel") };
  d.draw.toolbar.finish = { title: t("আঁকা শেষ করুন", "Finish drawing"), text: t("শেষ", "Finish") };
  d.draw.toolbar.undo = { title: t("শেষ বিন্দু মুছুন", "Delete last point"), text: t("শেষ বিন্দু মুছুন", "Delete last point") };
  d.draw.handlers.polygon.tooltip = {
    start: t("প্লটের একটি কোণে ক্লিক করুন।", "Click a corner of the plot."),
    cont: t("পরের কোণে ক্লিক করুন।", "Click the next corner."),
    end: t("প্রথম বিন্দুতে ক্লিক করে সীমানা বন্ধ করুন।", "Click the first point to close the boundary."),
  };
  d.draw.handlers.polyline.error = `<strong>${t("সীমানার রেখা একে অপরকে কাটতে পারবে না।", "Boundary lines cannot cross each other.")}</strong>`;
  d.edit.toolbar.buttons = {
    edit: t("সীমানা বদলান", "Edit boundary"), editDisabled: t("বদলানোর মতো সীমানা নেই", "No boundary to edit"),
    remove: t("সীমানা মুছুন", "Delete boundary"), removeDisabled: t("মোছার মতো সীমানা নেই", "No boundary to delete"),
  };
  d.edit.toolbar.actions = {
    save: { title: t("বদল রাখুন", "Save changes"), text: t("রাখুন", "Save") },
    cancel: { title: t("বদল বাতিল করুন", "Cancel changes"), text: t("বাতিল", "Cancel") },
    clearAll: { title: t("সব মুছুন", "Clear all"), text: t("সব মুছুন", "Clear all") },
  };
  d.edit.handlers.edit.tooltip = { text: t("কোণগুলো টেনে সীমানা বদলান।", "Drag the corners to change the boundary."), subtext: t("বাতিল করলে আগের সীমানা থাকবে।", "Cancel keeps the old boundary.") };
  d.edit.handlers.remove.tooltip = { text: t("মুছতে সীমানায় ক্লিক করুন।", "Click a boundary to delete it.") };
}

interface PlotMapProps {
  landId: string;
  geometry: PlotGeometry | null;
  onSaved: (geometry: PlotGeometry) => void;
}

export default function PlotMap({ landId, geometry, onSaved }: PlotMapProps) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const el = useRef<HTMLDivElement>(null);
  const drawn = useRef<Leaflet.FeatureGroup | null>(null);
  const [dirty, setDirty] = useState(false);
  const [hasShape, setHasShape] = useState(Boolean(geometry));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const initial = useRef(geometry);

  useEffect(() => {
    let map: Leaflet.Map | null = null;
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet-draw"); // adds L.Control.Draw to the global L that leaflet sets
      if (cancelled || !el.current) return;
      drawLabels(L, en);
      // wheel zoom only after a click on the map, so scrolling the page never zooms it by accident
      map = L.map(el.current, { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM, maxZoom: 19, zoomControl: false, scrollWheelZoom: false });
      map.on("click", () => map?.scrollWheelZoom.enable());
      map.on("mouseout", () => map?.scrollWheelZoom.disable());
      L.control.zoom({ zoomInTitle: en ? "Zoom in" : "কাছে আনুন", zoomOutTitle: en ? "Zoom out" : "দূরে নিন" }).addTo(map);
      // Esri has no zoom-19 imagery in much of rural Bangladesh: stretch zoom-18 tiles instead
      L.tileLayer(ESRI_URL, { attribution: ESRI_ATTRIBUTION, maxZoom: 19, maxNativeZoom: 18 }).addTo(map);
      const group = new L.FeatureGroup().addTo(map);
      drawn.current = group;
      const style = { color: "#f59e0b", weight: 3, fillOpacity: 0.15 };
      if (initial.current) {
        const layer = L.geoJSON(initial.current, { style });
        layer.eachLayer((l) => group.addLayer(l));
        map.fitBounds(group.getBounds(), { maxZoom: 18, padding: [24, 24] });
      }
      map.addControl(new L.Control.Draw({
        position: "topright",
        draw: {
          polygon: { allowIntersection: false, showArea: false, shapeOptions: style },
          polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false,
        },
        edit: { featureGroup: group },
      }));
      map.on(L.Draw.Event.CREATED, (e) => {
        group.clearLayers(); // one plot outline per land
        group.addLayer((e as Leaflet.DrawEvents.Created).layer);
        setHasShape(true); setDirty(true); setMessage(null);
      });
      map.on(L.Draw.Event.EDITED, () => { setDirty(true); setMessage(null); });
      map.on(L.Draw.Event.DELETED, () => { setHasShape(group.getLayers().length > 0); setDirty(true); setMessage(null); });
    })();
    return () => { cancelled = true; map?.remove(); };
    // Rebuilt when the language changes so the drawing toolbar labels follow it.
  }, [en]);

  const save = async () => {
    const layer = drawn.current?.getLayers()[0] as Leaflet.Polygon | undefined;
    if (!layer) return;
    const shape = layer.toGeoJSON().geometry as PlotGeometry;
    setSaving(true);
    setMessage(null);
    try {
      await api.saveLandGeometry(landId, shape);
      setDirty(false);
      setMessage({ ok: true, text: t("প্লটের সীমানা রাখা হয়েছে।", "Plot boundary saved.") });
      onSaved(shape);
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message.replace("Value error, ", "") : t("সীমানা রাখা যায়নি।", "Could not save the boundary.") });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-2">
      {/* relative z-0 isolate: Leaflet's panes use z-index up to 1000; keep them under the sticky header */}
      <div ref={el} className="relative z-0 isolate h-80 w-full overflow-hidden border-y border-line sm:h-96 sm:rounded-[var(--radius-card)] sm:border-x" role="application" aria-label={t("প্লটের সীমানা আঁকার মানচিত্র", "Map for drawing the plot boundary")} />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 sm:px-0">
        <button type="button" onClick={save} disabled={!dirty || !hasShape || saving} className="min-h-11 rounded-lg border border-accent bg-surface px-4 py-2 text-sm font-semibold text-accent">
          {saving ? t("রাখা হচ্ছে…", "Saving…") : t("সীমানা রাখুন", "Save boundary")}
        </button>
        <span className="text-xs text-muted">{t("মাউসের চাকা দিয়ে জুম করতে আগে মানচিত্রে একবার ক্লিক করুন।", "Click the map once before zooming with the mouse wheel.")}</span>
        {message && <span role="status" className={`text-sm ${message.ok ? "text-muted" : "text-bad"}`}>{message.text}</span>}
      </div>
    </div>
  );
}
