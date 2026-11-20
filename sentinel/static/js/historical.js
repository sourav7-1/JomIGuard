/* Collection page: draw an area, download the February 2025 GeoTIFF +
   matching high-resolution screenshot, track progress, download the ZIP. */

(function () {
    "use strict";

    const NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse";
    const BOUNDARY_URL = "/static/data/bangladesh_boundary.geojson";
    const PIXEL_SIZE_DEG = 10 / 111319.49079327357;
    let MAX_TOTAL_PIXELS = 60000000; // replaced by the server's limit from /historical/config
    let driveConfigured = false;
    const POLL_MS = 1500;

    const $ = (id) => document.getElementById(id);

    // ------------------------------------------------------------------
    // Map
    // ------------------------------------------------------------------

    const map = L.map("hist-map", { zoomControl: false, preferCanvas: false }).setView([23.7, 90.35], 7);

    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19,
        maxNativeZoom: 19,
        attribution: "Imagery &copy; Esri"
    }).addTo(map);

    L.control.zoom({ position: "topright" }).addTo(map);

    const FullscreenControl = L.Control.extend({
        options: { position: "topright" },
        onAdd: function () {
            const wrap = L.DomUtil.create("div", "leaflet-bar map-fs-btn");
            const link = L.DomUtil.create("a", "", wrap);
            link.href = "#";
            link.title = "Fullscreen";
            link.textContent = "⛶ Fullscreen";
            L.DomEvent.on(link, "click", function (event) {
                L.DomEvent.preventDefault(event);
                const el = $("hist-map");
                if (!document.fullscreenElement) {
                    (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
                } else {
                    document.exitFullscreen();
                }
            });
            L.DomEvent.disableClickPropagation(wrap);
            this._link = link;
            return wrap;
        }
    });
    const fullscreenControl = new FullscreenControl();
    map.addControl(fullscreenControl);
    document.addEventListener("fullscreenchange", function () {
        fullscreenControl._link.textContent = document.fullscreenElement ? "✕ Exit fullscreen" : "⛶ Fullscreen";
        setTimeout(() => map.invalidateSize(), 150);
    });

    const drawnItems = new L.FeatureGroup().addTo(map);
    const AOI_STYLE = { color: "#facc15", weight: 2.5, fillColor: "#facc15", fillOpacity: 0.12 };
    map.addControl(new L.Control.Draw({
        position: "topright",
        draw: {
            polygon: { allowIntersection: false, showArea: true, metric: true, shapeOptions: AOI_STYLE },
            rectangle: { shapeOptions: AOI_STYLE, metric: true },
            polyline: false, circle: false, circlemarker: false, marker: false
        },
        edit: { featureGroup: drawnItems, remove: true }
    }));

    // ------------------------------------------------------------------
    // Bangladesh boundary: outline + darkened outside, so the country's
    // shape and extent read clearly over the imagery.
    // ------------------------------------------------------------------

    // Official BBS boundary (rivers, estuary, islands and chars included),
    // clipped to the LSIB international border. Two levels of detail: a
    // light overview (~45 m) and a ~2 m version swapped in from zoom 10.
    const BOUNDARY_DETAIL_URL = "/static/data/bangladesh_boundary_detail.geojson";
    const DETAIL_ZOOM = 10;
    // Own pane below the overlay pane, so the selected area is always drawn on top.
    map.createPane("boundaryPane").style.zIndex = 350;
    const boundaryRenderer = L.canvas({ padding: 0.5, pane: "boundaryPane" });
    let boundaryPolygons = []; // [[ring of [lng, lat]], ...] outer rings only
    let boundaryLayers = [];
    let boundaryLevel = null; // "overview" | "detail"
    let detailGeojson = null;
    let detailLoading = false;

    function renderBoundary(geojson, level) {
        boundaryLayers.forEach((layer) => map.removeLayer(layer));
        const geometry = geojson.features[0].geometry;
        const parts = geometry.type === "MultiPolygon" ? geometry.coordinates : [geometry.coordinates];
        boundaryPolygons = parts.map((polygon) => polygon[0]);

        const world = [[-89.9, -179.9], [-89.9, 179.9], [89.9, 179.9], [89.9, -179.9]];
        const holes = boundaryPolygons.map((ring) => ring.map(([lng, lat]) => [lat, lng]));
        boundaryLayers = [
            L.polygon([world, ...holes], {
                stroke: false, fillColor: "#020617", fillOpacity: 0.42, interactive: false, renderer: boundaryRenderer
            }),
            L.geoJSON(geojson, { interactive: false, renderer: boundaryRenderer, smoothFactor: 0.5,
                style: { color: "#020617", weight: 6, opacity: 0.5, fill: false } }),
            L.geoJSON(geojson, { interactive: false, renderer: boundaryRenderer, smoothFactor: 0.5,
                style: { color: "#22d3ee", weight: 2.4, opacity: 1, fill: false, lineJoin: "round" } })
        ];
        boundaryLayers.forEach((layer) => layer.addTo(map));
        boundaryLevel = level;
        return boundaryLayers[2];
    }

    function maybeLoadDetailBoundary() {
        const wantDetail = map.getZoom() >= DETAIL_ZOOM;
        if (wantDetail && boundaryLevel !== "detail") {
            if (detailGeojson) {
                renderBoundary(detailGeojson, "detail");
            } else if (!detailLoading) {
                detailLoading = true;
                fetch(BOUNDARY_DETAIL_URL)
                    .then((response) => response.json())
                    .then((geojson) => {
                        detailGeojson = geojson;
                        if (map.getZoom() >= DETAIL_ZOOM) renderBoundary(geojson, "detail");
                    })
                    .catch((error) => console.warn("Detailed boundary could not be loaded:", error))
                    .finally(() => { detailLoading = false; });
            }
        } else if (!wantDetail && boundaryLevel === "detail" && overviewGeojson) {
            renderBoundary(overviewGeojson, "overview");
        }
    }

    let overviewGeojson = null;
    fetch(BOUNDARY_URL)
        .then((response) => response.json())
        .then((geojson) => {
            overviewGeojson = geojson;
            const outline = renderBoundary(geojson, "overview");
            if (!currentJob) map.fitBounds(outline.getBounds(), { padding: [20, 20] });
            maybeLoadDetailBoundary();
            updatePlaceName();
        })
        .catch((error) => console.warn("Bangladesh boundary could not be loaded:", error));

    map.on("zoomend", maybeLoadDetailBoundary);

    function pointInRing(lng, lat, ring) {
        let inside = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            const [xi, yi] = ring[i];
            const [xj, yj] = ring[j];
            if ((yi > lat) !== (yj > lat) && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
        }
        return inside;
    }

    function insideBangladesh(lng, lat) {
        return boundaryPolygons.some((ring) => pointInRing(lng, lat, ring));
    }

    // ------------------------------------------------------------------
    // Current place name (top-left), from the map center
    // ------------------------------------------------------------------

    const PlaceControl = L.Control.extend({
        options: { position: "topleft" },
        onAdd: function () {
            const box = L.DomUtil.create("div", "place-pill");
            box.innerHTML = '<div class="place-name">Bangladesh</div><div class="place-context">Move or zoom the map</div><div class="place-coords"></div>';
            return box;
        }
    });
    const placeControl = new PlaceControl();
    map.addControl(placeControl);
    const placeBox = placeControl.getContainer();

    const placeCache = new Map();
    let placeTimer = null;
    let placeAbort = null;
    let lastNominatimAt = 0;

    function nominatimZoom(mapZoom) {
        if (mapZoom <= 5) return 3;
        if (mapZoom <= 7) return 5;
        if (mapZoom <= 9) return 8;
        if (mapZoom <= 11) return 10;
        if (mapZoom <= 13) return 12;
        if (mapZoom <= 15) return 14;
        return 16;
    }

    // Area-level names only (no roads/buildings): the pill names the area
    // being viewed, from neighbourhood up to country depending on zoom.
    const LEVELS = [
        ["neighbourhood", 15], ["quarter", 15], ["hamlet", 14], ["suburb", 13], ["village", 13],
        ["town", 12], ["city_district", 12], ["city", 11], ["municipality", 11], ["county", 9],
        ["state_district", 8], ["state", 6], ["country", 0]
    ];

    function describePlace(address, mapZoom) {
        const parts = [];
        LEVELS.forEach(([key, minZoom]) => {
            const value = address[key];
            if (value && !parts.some((p) => p.value === value)) parts.push({ key, value, minZoom });
        });
        const eligible = parts.filter((p) => mapZoom >= p.minZoom);
        const primary = eligible[0] || parts[parts.length - 1];
        if (!primary) return null;
        const context = parts.slice(parts.indexOf(primary) + 1).map((p) => p.value);
        return { name: primary.value, context: context.join(" · ") };
    }

    function renderPlace(name, context, lat, lng, outside) {
        placeBox.classList.remove("loading");
        placeBox.classList.toggle("outside", Boolean(outside));
        placeBox.querySelector(".place-name").textContent = name;
        placeBox.querySelector(".place-context").textContent = context || "";
        placeBox.querySelector(".place-coords").textContent = `${lat.toFixed(5)}°N, ${lng.toFixed(5)}°E · zoom ${map.getZoom()}`;
    }

    async function updatePlaceName() {
        const center = map.getCenter();
        const zoom = map.getZoom();
        const nz = nominatimZoom(zoom);
        const outside = boundaryPolygons.length > 0 && !insideBangladesh(center.lng, center.lat);
        const key = `${nz}:${center.lat.toFixed(nz >= 14 ? 3 : 2)},${center.lng.toFixed(nz >= 14 ? 3 : 2)}`;

        if (zoom <= 6) {
            renderPlace(outside ? "Outside Bangladesh" : "Bangladesh", outside ? "" : "People's Republic of Bangladesh", center.lat, center.lng, outside);
            return;
        }
        if (placeCache.has(key)) {
            const cached = placeCache.get(key);
            renderPlace(cached.name, (outside ? "Outside Bangladesh · " : "") + cached.context, center.lat, center.lng, outside);
            return;
        }

        if (placeAbort) placeAbort.abort();
        placeAbort = new AbortController();
        placeBox.classList.add("loading");
        // Nominatim usage policy: at most one request per second.
        const wait = Math.max(0, 1100 - (Date.now() - lastNominatimAt));
        if (wait) await new Promise((resolve) => setTimeout(resolve, wait));
        lastNominatimAt = Date.now();
        try {
            const url = `${NOMINATIM_REVERSE}?format=jsonv2&addressdetails=1&lat=${center.lat}&lon=${center.lng}&zoom=${nz}`;
            const response = await fetch(url, { headers: { "Accept-Language": "en" }, signal: placeAbort.signal });
            const data = await response.json();
            let place;
            if (data.error || !data.address) {
                place = { name: outside ? "Outside Bangladesh" : "Unnamed area", context: outside ? "" : "No named place here (open water or field)" };
            } else {
                place = describePlace(data.address, zoom) || { name: data.name || "Unnamed area", context: "" };
            }
            placeCache.set(key, place);
            renderPlace(place.name, (outside && place.name !== "Outside Bangladesh" ? "Outside Bangladesh · " : "") + place.context, center.lat, center.lng, outside);
        } catch (error) {
            if (error.name !== "AbortError") {
                renderPlace(outside ? "Outside Bangladesh" : "Bangladesh", "Place name lookup unavailable", center.lat, center.lng, outside);
            }
        }
    }

    map.on("moveend", function () {
        clearTimeout(placeTimer);
        placeTimer = setTimeout(updatePlaceName, 450);
    });

    // ------------------------------------------------------------------
    // Area selection
    // ------------------------------------------------------------------

    let selectedCoordinates = null;

    function coordinatesFromLayer(layer) {
        return layer.getLatLngs()[0].map((point) => [point.lng, point.lat]);
    }

    function describeAoi(coordinates) {
        const lngs = coordinates.map((p) => p[0]);
        const lats = coordinates.map((p) => p[1]);
        const midLat = (Math.min(...lats) + Math.max(...lats)) / 2;
        const widthM = (Math.max(...lngs) - Math.min(...lngs)) * 111320 * Math.cos((midLat * Math.PI) / 180);
        const heightM = (Math.max(...lats) - Math.min(...lats)) * 110574;
        const latlngs = coordinates.map(([lng, lat]) => L.latLng(lat, lng));
        const areaKm2 = L.GeometryUtil ? L.GeometryUtil.geodesicArea(latlngs) / 1e6 : (widthM * heightM) / 1e6;
        // Same grid as the server: 10 m expressed in degrees on both axes.
        const cols = Math.ceil((Math.max(...lngs) - Math.min(...lngs)) / PIXEL_SIZE_DEG) + 1;
        const rows = Math.ceil((Math.max(...lats) - Math.min(...lats)) / PIXEL_SIZE_DEG) + 1;
        return { areaKm2, widthM, heightM, cols, rows, px: cols * rows, tooLarge: cols * rows > MAX_TOTAL_PIXELS };
    }

    function updateAoiSummary() {
        const box = $("aoi-summary");
        if (!selectedCoordinates) {
            box.textContent = "No area drawn yet.";
            box.classList.remove("ok");
            return;
        }
        const info = describeAoi(selectedCoordinates);
        const outside = boundaryPolygons.length && !selectedCoordinates.some(([lng, lat]) => insideBangladesh(lng, lat));
        box.classList.toggle("ok", !info.tooLarge);
        box.innerHTML =
            `<strong>${info.areaKm2 < 1 ? (info.areaKm2 * 100).toFixed(1) + " ha" : info.areaKm2.toFixed(2) + " km²"}</strong>` +
            ` · ${(info.widthM / 1000).toFixed(2)} × ${(info.heightM / 1000).toFixed(2)} km` +
            ` · GeoTIFF ≈ ${info.cols} × ${info.rows} px` +
            (info.tooLarge ? `<div class="output-meta error">Too large for one download -- please draw a smaller area.</div>` : "") +
            (outside ? `<div class="output-meta" style="color:#fde68a">This area is outside Bangladesh.</div>` : "");
    }

    map.on(L.Draw.Event.CREATED, function (event) {
        drawnItems.clearLayers();
        drawnItems.addLayer(event.layer);
        selectedCoordinates = coordinatesFromLayer(event.layer);
        updateAoiSummary();
        suggestAreaName(selectedCoordinates);
    });

    map.on(L.Draw.Event.EDITED, function () {
        const layer = drawnItems.getLayers()[0];
        selectedCoordinates = layer ? coordinatesFromLayer(layer) : null;
        updateAoiSummary();
    });

    map.on(L.Draw.Event.DELETED, function () {
        selectedCoordinates = drawnItems.getLayers().length ? coordinatesFromLayer(drawnItems.getLayers()[0]) : null;
        updateAoiSummary();
    });

    async function suggestAreaName(coordinates) {
        const lng = coordinates.reduce((s, p) => s + p[0], 0) / coordinates.length;
        const lat = coordinates.reduce((s, p) => s + p[1], 0) / coordinates.length;
        try {
            const response = await fetch(`${NOMINATIM_REVERSE}?format=jsonv2&lat=${lat}&lon=${lng}&zoom=14`, { headers: { "Accept-Language": "en" } });
            if (!response.ok) return;
            const address = (await response.json()).address || {};
            const locality = address.suburb || address.village || address.town || address.neighbourhood || "";
            const district = address.state_district || address.county || address.city || "";
            const suggestion = [district, locality].filter(Boolean).join("_").replace(/\s+/g, "_").replace(/_District$/i, "");
            if (suggestion) {
                $("suggested-name").textContent = suggestion;
                $("use-suggested-btn").hidden = false;
                if (!$("area-name-input").value.trim()) $("area-name-input").value = suggestion;
            }
        } catch (error) {
            console.warn("Name suggestion failed:", error);
        }
    }

    $("use-suggested-btn").addEventListener("click", function () {
        const suggested = $("suggested-name").textContent;
        if (suggested && suggested !== "-") $("area-name-input").value = suggested;
    });

    // ------------------------------------------------------------------
    // Job start / progress
    // ------------------------------------------------------------------

    let currentJob = null;
    let pollTimer = null;

    function showError(text) {
        $("start-error").textContent = text;
        $("start-error").hidden = !text;
    }

    $("start-collection-btn").addEventListener("click", async function () {
        showError("");
        if (!selectedCoordinates) return showError("Draw an area on the map first.");
        if (describeAoi(selectedCoordinates).tooLarge) return showError("This area is too large for one download. Please draw a smaller area.");
        const areaName = $("area-name-input").value.trim();
        if (!areaName) {
            $("area-name-input").focus();
            return showError("Enter an area name.");
        }

        const button = this;
        button.disabled = true;
        button.textContent = "Starting…";
        try {
            const response = await fetch("/historical/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    coordinates: selectedCoordinates,
                    area_name: areaName,
                    export_destination: "local"
                })
            });
            const data = await response.json();
            if (!data.success) return showError(data.message || "Could not start the download.");
            setCurrentJob(data.job);
            loadJobList();
            $("progress-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
        } catch (error) {
            showError("Network error while starting the download.");
        } finally {
            button.disabled = false;
            button.textContent = "Start download";
        }
    });

    function setCurrentJob(job) {
        currentJob = job;
        $("progress-card").hidden = false;
        history.replaceState(null, "", `/historical?job_id=${job.job_id}`);
        renderJob(job);
        startPolling();
        highlightCurrentJob();
    }

    function isBusy(state) {
        return ["QUEUED", "PROCESSING", "EXPORTING", "RETRYING"].includes(state);
    }

    function setBadge(element, state) {
        element.className = "badge " + state;
        element.textContent = state;
    }

    function setLinkEnabled(link, enabled, href) {
        link.classList.toggle("is-disabled", !enabled);
        link.setAttribute("aria-disabled", String(!enabled));
        if (href) link.href = href;
    }

    function renderJob(job) {
        // Elements are updated in place (never rebuilt), so a click on a
        // button is never lost to a polling re-render.
        $("job-area-label").textContent = `· ${job.area_name}`;

        const yearKey = Object.keys(job.years).sort().pop();
        const record = job.years[yearKey];
        setBadge($("tif-badge"), record.state);
        $("tif-retry-btn").hidden = record.state !== "FAILED";
        const tifMeta = $("tif-meta");
        tifMeta.classList.toggle("error", record.state === "FAILED");
        if (record.state === "FAILED") {
            tifMeta.textContent = record.error || "Failed.";
        } else if (record.raster_width) {
            tifMeta.textContent = `${record.file_name} · ${record.raster_width}×${record.raster_height} px · quality ${record.quality_flag || "-"}` +
                (record.usable_pixel_percentage != null ? ` · ${record.usable_pixel_percentage.toFixed(1)}% usable` : "") +
                ` · ${record.sentinel2_scene_count} S2 / ${record.sentinel1_scene_count} S1 scenes`;
        } else if (record.state === "READY" || record.state === "DOWNLOADED") {
            tifMeta.textContent = record.drive_task_id ? `Sent to Google Drive (task ${record.drive_task_id}).` : "Ready.";
        } else {
            tifMeta.textContent = {
                QUEUED: "Queued…",
                RETRYING: "Retrying…",
                PROCESSING: "Building the February 2025 composite in Earth Engine…",
                EXPORTING: "Downloading the GeoTIFF…"
            }[record.state] || record.state;
        }

        const labelingInfo = job.labeling || {};
        const shotState = labelingInfo.reference_ready ? "READY" : (labelingInfo.screenshot_state || "QUEUED");
        setBadge($("shot-badge"), shotState);
        $("shot-retry-btn").hidden = shotState !== "FAILED";
        const shotMeta = $("shot-meta");
        shotMeta.classList.toggle("error", shotState === "FAILED");
        const info = labelingInfo.reference_info;
        if (shotState === "READY" && info) {
            shotMeta.textContent = `${info.width}×${info.height} px · ${(info.ground_resolution_m || 0).toFixed(2)} m/px · zoom ${info.zoom} · validated (no “map not available” tiles)`;
        } else if (shotState === "FAILED") {
            shotMeta.textContent = labelingInfo.error || "Failed.";
        } else {
            shotMeta.textContent = shotState === "PROCESSING" ? "Fetching and validating basemap tiles…" : "Queued…";
        }

        const tifReady = Boolean(record.file_path) && ["READY", "DOWNLOADED"].includes(record.state);
        const shotReady = shotState === "READY";
        $("download-zip-btn").disabled = !(tifReady || shotReady) || zipBusy;
        setLinkEnabled($("download-screenshot-link"), shotReady, `/historical/screenshot/${job.job_id}`);
        setLinkEnabled($("open-labeling-link"), tifReady || shotReady, `/labeling?job_id=${job.job_id}`);
        $("drive-save-btn").disabled = !driveConfigured || !(tifReady || shotReady);
        $("nav-labeling-link").href = `/labeling?job_id=${job.job_id}`;

        const running = isBusy(record.state) || isBusy(shotState);
        if (!running) {
            stopPolling();
            if (!zipBusy) {
                $("download-status").textContent = tifReady && shotReady
                    ? "Both files are ready. The ZIP contains the GeoTIFF, the screenshot and (after labeling) the masks for both models."
                    : (tifReady || shotReady ? "One output failed -- use Retry, or download what is available." : "");
            }
        } else if (!zipBusy) {
            $("download-status").textContent = "Working… this page updates automatically.";
        }
    }

    async function refreshStatus() {
        if (!currentJob) return;
        try {
            const response = await fetch(`/historical/status/${currentJob.job_id}`);
            const data = await response.json();
            if (data.success) {
                currentJob = data.job;
                renderJob(data.job);
            }
        } catch (error) {
            console.warn("Status refresh failed:", error);
        }
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(refreshStatus, POLL_MS);
    }

    function stopPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        loadJobList();
    }

    async function postAndRefresh(url) {
        const response = await fetch(url, { method: "POST" });
        const data = await response.json();
        if (!data.success) $("download-status").textContent = data.message || "Request failed.";
        await refreshStatus();
        startPolling();
    }

    $("tif-retry-btn").addEventListener("click", function () {
        if (!currentJob) return;
        const year = Object.keys(currentJob.years).sort().pop();
        postAndRefresh(`/historical/retry/${currentJob.job_id}/${year}`);
    });

    $("shot-retry-btn").addEventListener("click", function () {
        if (currentJob) postAndRefresh(`/historical/retry-screenshot/${currentJob.job_id}`);
    });

    // ------------------------------------------------------------------
    // ZIP download: starts on the first click, with visible progress.
    // ------------------------------------------------------------------

    let zipBusy = false;

    $("download-zip-btn").addEventListener("click", async function () {
        if (!currentJob || zipBusy) return;
        zipBusy = true;
        const button = this;
        const status = $("download-status");
        button.disabled = true;
        button.textContent = "Preparing ZIP…";
        status.textContent = "Packing the dataset…";
        try {
            const response = await fetch(`/historical/download-zip/${currentJob.job_id}`);
            if (!response.ok) {
                let message = `Server returned ${response.status}`;
                try { message = (await response.json()).message || message; } catch (e) { /* not JSON */ }
                throw new Error(message);
            }
            const disposition = response.headers.get("Content-Disposition") || "";
            const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
            const fileName = match ? decodeURIComponent(match[1]) : `${currentJob.area_name}_dataset.zip`;
            const total = Number(response.headers.get("Content-Length")) || 0;

            const reader = response.body.getReader();
            const chunks = [];
            let received = 0;
            button.textContent = "Downloading…";
            for (;;) {
                const { done, value } = await reader.read();
                if (done) break;
                chunks.push(value);
                received += value.length;
                status.textContent = total
                    ? `Downloading ${(received / 1048576).toFixed(1)} / ${(total / 1048576).toFixed(1)} MB (${Math.round((received / total) * 100)}%)`
                    : `Downloading ${(received / 1048576).toFixed(1)} MB…`;
            }
            const url = URL.createObjectURL(new Blob(chunks, { type: "application/zip" }));
            const link = document.createElement("a");
            link.href = url;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 30000);
            status.textContent = `Saved ${fileName} (${(received / 1048576).toFixed(1)} MB).`;
        } catch (error) {
            status.textContent = `Download failed: ${error.message}`;
        } finally {
            zipBusy = false;
            button.textContent = "Download dataset (ZIP)";
            button.disabled = false;
            refreshStatus();
        }
    });

    // Disabled links must not navigate.
    ["download-screenshot-link", "open-labeling-link"].forEach((id) => {
        $(id).addEventListener("click", function (event) {
            if (this.classList.contains("is-disabled")) event.preventDefault();
        });
    });

    // ------------------------------------------------------------------
    // Recent jobs
    // ------------------------------------------------------------------

    function highlightCurrentJob() {
        document.querySelectorAll(".job-item").forEach((item) => {
            item.classList.toggle("current", Boolean(currentJob) && item.dataset.jobId === currentJob.job_id);
        });
    }

    async function loadJobList() {
        try {
            const data = await (await fetch("/historical/jobs")).json();
            const list = $("job-list");
            if (!data.success || !data.jobs.length) {
                list.innerHTML = '<div class="hint">No areas collected yet.</div>';
                return;
            }
            list.innerHTML = "";
            data.jobs.forEach((job) => {
                const item = document.createElement("button");
                item.type = "button";
                item.className = "job-item";
                item.dataset.jobId = job.job_id;
                const created = job.created_at ? new Date(job.created_at).toLocaleString() : "";
                const yearsText = job.years.length > 1 ? `${job.years[0]}–${job.years[job.years.length - 1]} (older job)` : String(job.years[0] || "");
                item.innerHTML = `<span><strong></strong><small></small></span><span class="badge"></span>`;
                item.querySelector("strong").textContent = job.area_name;
                item.querySelector("small").textContent = `${yearsText} · ${created}`;
                const badge = item.querySelector(".badge");
                const labeled = job.mask_saved;
                badge.textContent = labeled ? "LABELED" : job.job_status;
                badge.classList.add(labeled || job.job_status === "COMPLETED" ? "READY" : "PROCESSING");
                item.addEventListener("click", () => openJob(job.job_id));
                list.appendChild(item);
            });
            highlightCurrentJob();
        } catch (error) {
            console.warn("Could not load job list:", error);
        }
    }

    async function openJob(jobId) {
        const data = await (await fetch(`/historical/status/${jobId}`)).json();
        if (!data.success) return;
        setCurrentJob(data.job);
        if (data.job.coordinates && data.job.coordinates.length) {
            drawnItems.clearLayers();
            const layer = L.polygon(data.job.coordinates.map(([lng, lat]) => [lat, lng]), AOI_STYLE);
            drawnItems.addLayer(layer);
            selectedCoordinates = data.job.coordinates;
            updateAoiSummary();
            map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 17 });
        }
    }

    fetch("/historical/config").then((r) => r.json()).then((config) => {
        if (config.max_total_pixels) MAX_TOTAL_PIXELS = config.max_total_pixels;
        driveConfigured = Boolean(config.google_client_id);
        window.DriveSave.configure(config.google_client_id);
        window.DriveSave.attachPanel({
            input: $("drive-link-input"),
            button: $("drive-save-btn"),
            status: $("drive-status"),
            getJobId: () => currentJob && currentJob.job_id
        });
        if (currentJob) renderJob(currentJob);
    }).catch((error) => console.warn("Config could not be loaded:", error));

    loadJobList();
    const initialJobId = new URLSearchParams(window.location.search).get("job_id");
    if (initialJobId) openJob(initialJobId);
})();
