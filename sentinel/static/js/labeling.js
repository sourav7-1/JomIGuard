/* Manual polygon labeling.

   Coordinates: polygon points are kept in the pixel space of the image
   currently displayed ("surface"). Every surface is georeferenced:
     - screenshot: Web Mercator world pixels (zoom + origin from the server)
     - rgb / ndvi / false_color: the GeoTIFF's own grid (affine transform),
       upscaled by an integer factor
   so switching surfaces converts every point through lon/lat instead of
   discarding the polygons. On save, the points and the surface name are
   sent to the server, which converts them to lon/lat and rasterizes masks
   for BOTH the GeoTIFF grid and the screenshot grid.

   The canvas only ever covers the visible viewport; zoom/pan is a view
   transform, so even a 4096 px screenshot redraws quickly. */

(function () {
    "use strict";

    const $ = (id) => document.getElementById(id);
    const canvas = $("label-canvas");
    const ctx = canvas.getContext("2d");
    const viewport = $("canvas-viewport");

    const CLOSE_RADIUS_SCREEN_PX = 10;
    const VERTEX_HIT_SCREEN_PX = 8;
    const EDGE_HIT_SCREEN_PX = 6;
    const DRAG_THRESHOLD_SCREEN_PX = 3;
    // Freehand: sample the stroke every ~2 screen px, then simplify it so the
    // saved polygon stays within ~1 screen px of what was drawn.
    const FREEHAND_MIN_STEP_SCREEN_PX = 2;
    const FREEHAND_SIMPLIFY_SCREEN_PX = 1.2;
    const FREEHAND_MIN_AREA_SCREEN_PX2 = 150; // smaller strokes are taps/slips, not regions
    const TAP_MAX_MOVE_SCREEN_PX = 10;
    const MIN_SCALE = 0.02;
    const MAX_SCALE = 16;

    // ---------------- State ----------------
    let labelClasses = [];
    let activeClassId = 0;
    let jobId = null;
    let year = null;
    let selectData = null; // /labeling/select-year response
    let currentMode = "screenshot";
    let baseImage = null;
    let surfaceSize = null; // {width, height} of the displayed image

    let polygons = []; // [{class_id, points: [[x, y], ...]}] in current surface pixels
    let undoStack = [];
    let redoStack = [];
    // Drawing state. currentPoints is the ONE unfinished polygon ("draft");
    // hoverPoint is the live cursor position used only for the rubber-band
    // preview segment and is cleared whenever a draft starts/ends, so the
    // preview can never connect to a previously finished polygon.
    let currentPoints = [];
    let hoverPoint = null;
    let lastClose = null; // {time, x, y} -- swallow the trailing click of a close
    let tool = "draw";
    let selectedIndex = -1;
    let dragVertex = null; // {polygon, vertex, startX, startY, active}
    let eraseTarget = null; // {type: "polygon", index} | {type: "draft"} under the cursor in Erase mode

    // Freehand stroke in progress (press-and-hold drawing): {pointerId, pointerType, points}
    let stroke = null;
    // Touch input: active fingers, two-finger pan/zoom gesture, and a
    // finger tap waiting to be confirmed (so the first finger of a pinch
    // never adds a point or selects something).
    const activeTouches = new Map();
    let gesture = null;
    let pendingTap = null;
    let polygonsVisible = true;
    let aoiVisible = true;
    let fillOpacity = 0.35;
    let dirty = false;
    let lastSavePayload = null;

    const view = { scale: 1, offsetX: 0, offsetY: 0 };
    let panState = null;
    let spaceHeld = false;

    // ---------------- Helpers ----------------
    function setStatus(text, isError) {
        const el = $("label-status");
        el.textContent = text;
        el.classList.toggle("error", Boolean(isError));
    }

    function classById(id) {
        return labelClasses.find((entry) => entry.id === id);
    }

    function hexToRgba(hex, alpha) {
        const v = hex.replace("#", "");
        return `rgba(${parseInt(v.slice(0, 2), 16)}, ${parseInt(v.slice(2, 4), 16)}, ${parseInt(v.slice(4, 6), 16)}, ${alpha})`;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    function markDirty() {
        dirty = true;
        updateSaveButton();
    }

    function updateSaveButton() {
        const button = $("save-mask-btn");
        if (button.textContent === "Saving…") return;
        button.disabled = !jobId || polygons.length === 0;
        button.textContent = dirty && polygons.length ? "Save labels  •  unsaved changes" : "Save labels";
    }

    // ---------------- Georeferencing ----------------
    const TILE = 256;

    function screenshotToLonLat([x, y]) {
        const info = selectData.reference_info;
        const n = TILE * Math.pow(2, info.zoom);
        const wx = info.origin_world_px_x + x;
        const wy = info.origin_world_px_y + y;
        const lon = (wx / n) * 360 - 180;
        const lat = (Math.atan(Math.sinh(Math.PI * (1 - (2 * wy) / n))) * 180) / Math.PI;
        return [lon, lat];
    }

    function lonLatToScreenshot([lon, lat]) {
        const info = selectData.reference_info;
        const n = TILE * Math.pow(2, info.zoom);
        const clampedLat = Math.max(Math.min(lat, 85.05112878), -85.05112878);
        const rad = (clampedLat * Math.PI) / 180;
        const wx = ((lon + 180) / 360) * n;
        const wy = ((1 - Math.asinh(Math.tan(rad)) / Math.PI) / 2) * n;
        return [wx - info.origin_world_px_x, wy - info.origin_world_px_y];
    }

    function nativeToLonLat([x, y]) {
        const [a, b, c, d, e, f] = selectData.geotiff.transform;
        const scale = selectData.preview_info.scale;
        const col = x / scale;
        const row = y / scale;
        return [a * col + b * row + c, d * col + e * row + f];
    }

    function lonLatToNative([lon, lat]) {
        const [a, b, c, d, e, f] = selectData.geotiff.transform;
        const scale = selectData.preview_info.scale;
        const det = a * e - b * d;
        const dx = lon - c;
        const dy = lat - f;
        return [((e * dx - b * dy) / det) * scale, ((a * dy - d * dx) / det) * scale];
    }

    function nativeIsGeographic() {
        return Boolean(selectData && selectData.geotiff && selectData.preview_info && selectData.geotiff.crs === "EPSG:4326");
    }

    function toLonLat(point, mode) {
        return mode === "screenshot" ? screenshotToLonLat(point) : nativeToLonLat(point);
    }

    function fromLonLat(lonlat, mode) {
        return mode === "screenshot" ? lonLatToScreenshot(lonlat) : lonLatToNative(lonlat);
    }

    function canGeoreference(mode) {
        if (!selectData) return false;
        if (mode === "screenshot") return Boolean(selectData.screenshot_ready && selectData.reference_info);
        return nativeIsGeographic();
    }

    // ---------------- View transform ----------------
    function screenToImage(clientX, clientY) {
        const rect = canvas.getBoundingClientRect();
        return [(clientX - rect.left - view.offsetX) / view.scale, (clientY - rect.top - view.offsetY) / view.scale];
    }

    function resizeCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const width = viewport.clientWidth;
        const height = viewport.clientHeight;
        canvas.width = Math.max(1, Math.round(width * dpr));
        canvas.height = Math.max(1, Math.round(height * dpr));
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        redraw();
    }

    function fitToScreen() {
        if (!surfaceSize) return;
        const width = viewport.clientWidth;
        const height = viewport.clientHeight;
        view.scale = Math.min(width / surfaceSize.width, height / surfaceSize.height) * 0.97;
        view.scale = Math.max(MIN_SCALE, Math.min(view.scale, 6));
        view.offsetX = (width - surfaceSize.width * view.scale) / 2;
        view.offsetY = (height - surfaceSize.height * view.scale) / 2;
        redraw();
    }

    function zoomAt(factor, clientX, clientY) {
        if (!surfaceSize) return;
        const rect = canvas.getBoundingClientRect();
        const sx = clientX === undefined ? rect.width / 2 : clientX - rect.left;
        const sy = clientY === undefined ? rect.height / 2 : clientY - rect.top;
        const newScale = Math.max(MIN_SCALE, Math.min(view.scale * factor, MAX_SCALE));
        const ix = (sx - view.offsetX) / view.scale;
        const iy = (sy - view.offsetY) / view.scale;
        view.scale = newScale;
        view.offsetX = sx - ix * newScale;
        view.offsetY = sy - iy * newScale;
        redraw();
    }

    // ---------------- Drawing ----------------
    function tracePath(points, close) {
        ctx.beginPath();
        points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        if (close) ctx.closePath();
    }

    function redraw() {
        const dpr = window.devicePixelRatio || 1;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        $("zoom-readout").textContent = `${Math.round(view.scale * 100)}%`;
        if (!baseImage || !surfaceSize) return;

        ctx.setTransform(dpr * view.scale, 0, 0, dpr * view.scale, dpr * view.offsetX, dpr * view.offsetY);
        // Past 100% show real pixels as crisp blocks, never interpolated detail.
        ctx.imageSmoothingEnabled = view.scale < 1;
        ctx.drawImage(baseImage, 0, 0, surfaceSize.width, surfaceSize.height);

        const px = 1 / view.scale; // one screen pixel in image units

        if (aoiVisible && selectData && selectData.job && canGeoreference(currentMode)) {
            const ring = selectData.job.coordinates.map((p) => fromLonLat(p, currentMode));
            tracePath(ring, true);
            ctx.setLineDash([8 * px, 5 * px]);
            ctx.lineWidth = 2 * px;
            ctx.strokeStyle = "#facc15";
            ctx.stroke();
            ctx.setLineDash([]);
        }

        const hasSelection = tool === "select" && selectedIndex >= 0 && Boolean(polygons[selectedIndex]);
        const eraseIndex = tool === "erase" && eraseTarget && eraseTarget.type === "polygon" ? eraseTarget.index : -1;

        if (polygonsVisible) {
            polygons.forEach((polygon, index) => {
                if (index === selectedIndex && hasSelection) return; // drawn last, on top
                const entry = classById(polygon.class_id);
                const color = entry ? entry.color : "#ffffff";
                const dim = hasSelection ? 0.45 : 1;
                tracePath(polygon.points, true);
                ctx.fillStyle = index === eraseIndex ? "rgba(239, 68, 68, 0.45)" : hexToRgba(color, fillOpacity * dim);
                ctx.fill();
                ctx.globalAlpha = dim;
                ctx.lineWidth = 2 * px;
                ctx.strokeStyle = color;
                ctx.stroke();
                ctx.globalAlpha = 1;
                if (index === eraseIndex) {
                    ctx.setLineDash([6 * px, 4 * px]);
                    ctx.lineWidth = 3 * px;
                    ctx.strokeStyle = "#ef4444";
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            });

            if (hasSelection) {
                const polygon = polygons[selectedIndex];
                const entry = classById(polygon.class_id);
                const color = entry ? entry.color : "#ffffff";
                tracePath(polygon.points, true);
                ctx.fillStyle = hexToRgba(color, Math.min(0.85, fillOpacity + 0.2));
                ctx.fill();
                ctx.lineJoin = "round";
                ctx.lineWidth = 6 * px; // white halo
                ctx.strokeStyle = "rgba(255, 255, 255, 0.95)";
                ctx.stroke();
                ctx.lineWidth = 3 * px;
                ctx.strokeStyle = color;
                ctx.stroke();
                polygon.points.forEach(([x, y], i) => {
                    const active = dragVertex && dragVertex.active && dragVertex.vertex === i;
                    const half = (active ? 6 : 4.5) * px;
                    ctx.beginPath();
                    ctx.rect(x - half, y - half, half * 2, half * 2);
                    ctx.fillStyle = active ? color : "#ffffff";
                    ctx.fill();
                    ctx.lineWidth = 1.5 * px;
                    ctx.strokeStyle = "#0f172a";
                    ctx.stroke();
                });
            }
        }

        if (currentPoints.length) {
            const eraseDraft = tool === "erase" && eraseTarget && eraseTarget.type === "draft";
            const entry = classById(activeClassId);
            const color = eraseDraft ? "#ef4444" : (entry ? entry.color : "#ffffff");
            tracePath(currentPoints, false);
            ctx.lineWidth = (eraseDraft ? 3 : 2) * px;
            ctx.strokeStyle = color;
            if (tool !== "draw" && !eraseDraft) ctx.setLineDash([5 * px, 4 * px]);
            ctx.stroke();
            ctx.setLineDash([]);
            // Rubber band: only from THIS draft's last point, only while drawing.
            if (tool === "draw" && hoverPoint) {
                const last = currentPoints[currentPoints.length - 1];
                ctx.beginPath();
                ctx.moveTo(last[0], last[1]);
                ctx.lineTo(hoverPoint[0], hoverPoint[1]);
                ctx.setLineDash([6 * px, 4 * px]);
                ctx.stroke();
                ctx.setLineDash([]);
            }
            currentPoints.forEach(([x, y], i) => {
                ctx.beginPath();
                ctx.arc(x, y, (i === 0 ? 6 : 4) * px, 0, Math.PI * 2);
                ctx.fillStyle = i === 0 && !eraseDraft ? "#ffffff" : color;
                ctx.fill();
                ctx.lineWidth = 1.5 * px;
                ctx.strokeStyle = "#0f172a";
                ctx.stroke();
            });
        }

        if (stroke && stroke.points.length) {
            const entry = classById(activeClassId);
            const color = entry ? entry.color : "#ffffff";
            ctx.lineJoin = "round";
            ctx.lineCap = "round";
            if (stroke.points.length >= 3) {
                tracePath(stroke.points, true);
                ctx.fillStyle = hexToRgba(color, fillOpacity * 0.6);
                ctx.fill();
            }
            tracePath(stroke.points, false);
            ctx.lineWidth = 2.5 * px;
            ctx.strokeStyle = color;
            ctx.stroke();
            // Dashed preview of the closing edge: releasing closes the shape here.
            if (stroke.points.length >= 2) {
                const first = stroke.points[0];
                const last = stroke.points[stroke.points.length - 1];
                ctx.beginPath();
                ctx.moveTo(last[0], last[1]);
                ctx.lineTo(first[0], first[1]);
                ctx.setLineDash([5 * px, 5 * px]);
                ctx.lineWidth = 1.5 * px;
                ctx.stroke();
                ctx.setLineDash([]);
            }
            ctx.lineCap = "butt";
        }
        updateContextBar();
    }

    // ---------------- Freehand ----------------
    function simplifyPath(points, tolerance) {
        // Ramer-Douglas-Peucker, iterative.
        if (points.length < 3) return points.slice();
        const keep = new Uint8Array(points.length);
        keep[0] = keep[points.length - 1] = 1;
        const stack = [[0, points.length - 1]];
        while (stack.length) {
            const [start, end] = stack.pop();
            let maxDist = 0;
            let index = -1;
            for (let i = start + 1; i < end; i++) {
                const d = distanceToSegment(points[i], points[start], points[end]);
                if (d > maxDist) { maxDist = d; index = i; }
            }
            if (index !== -1 && maxDist > tolerance) {
                keep[index] = 1;
                stack.push([start, index], [index, end]);
            }
        }
        return points.filter((_, i) => keep[i]);
    }

    function addStrokePoint(clientX, clientY) {
        const point = clampToImage(screenToImage(clientX, clientY));
        const last = stroke.points[stroke.points.length - 1];
        if (!last || Math.hypot(point[0] - last[0], point[1] - last[1]) * view.scale >= FREEHAND_MIN_STEP_SCREEN_PX) {
            stroke.points.push(point);
            return true;
        }
        return false;
    }

    function cancelStroke() {
        if (!stroke) return false;
        stroke = null;
        redraw();
        return true;
    }

    function finishStroke() {
        const drawn = stroke;
        stroke = null;
        if (!drawn) return;
        let points = simplifyPath(drawn.points, FREEHAND_SIMPLIFY_SCREEN_PX / view.scale);
        // If the stroke ended where it started, drop the duplicate end point.
        if (points.length >= 4) {
            const first = points[0];
            const last = points[points.length - 1];
            if (Math.hypot(first[0] - last[0], first[1] - last[1]) * view.scale < 6) points = points.slice(0, -1);
        }
        if (points.length < 3 || polygonAreaPx(points) * view.scale * view.scale < FREEHAND_MIN_AREA_SCREEN_PX2) {
            redraw();
            setStatus("That stroke was too small to be a region -- press, hold and draw around the area.", true);
            return;
        }
        snapshot();
        polygons.push({ class_id: activeClassId, points });
        markDirty();
        refreshLists();
        redraw();
        setStatus(`Freehand polygon added as "${classById(activeClassId).label}" (${points.length} points). Draw the next one, or Ctrl+Z to undo.`);
    }

    // ---------------- History ----------------
    function snapshot() {
        undoStack.push(JSON.stringify(polygons));
        if (undoStack.length > 200) undoStack.shift();
        redoStack = [];
    }

    function undo() {
        if (currentPoints.length) {
            currentPoints.pop();
            if (!currentPoints.length) hoverPoint = null;
            redraw();
            return;
        }
        if (!undoStack.length) return;
        redoStack.push(JSON.stringify(polygons));
        polygons = JSON.parse(undoStack.pop());
        selectedIndex = -1;
        markDirty();
        refreshLists();
        redraw();
    }

    function redo() {
        if (!redoStack.length) return;
        undoStack.push(JSON.stringify(polygons));
        polygons = JSON.parse(redoStack.pop());
        selectedIndex = -1;
        markDirty();
        refreshLists();
        redraw();
    }

    // ---------------- Polygon operations ----------------
    function closeCurrentPolygon(closeAt) {
        if (currentPoints.length < 3) {
            setStatus("A polygon needs at least 3 points.", true);
            return;
        }
        snapshot();
        polygons.push({ class_id: activeClassId, points: currentPoints.map((p) => [p[0], p[1]]) });
        resetDraft();
        // Where the closing click landed: a second click there right away
        // (end of a double-click) must not start a stray new drawing.
        lastClose = closeAt ? { time: performance.now(), x: closeAt[0], y: closeAt[1] } : null;
        markDirty();
        refreshLists();
        redraw();
        setStatus(`Polygon added as "${classById(activeClassId).label}". Keep drawing, or save when done.`);
    }

    function pointInPolygon([px, py], points) {
        let inside = false;
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
            const [xi, yi] = points[i];
            const [xj, yj] = points[j];
            if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
        }
        return inside;
    }

    function distanceToSegment([px, py], [ax, ay], [bx, by]) {
        const dx = bx - ax;
        const dy = by - ay;
        const lengthSq = dx * dx + dy * dy;
        const t = lengthSq ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSq)) : 0;
        return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
    }

    function distanceToRing(point, points, closed) {
        let best = Infinity;
        const n = points.length;
        if (n === 1) return Math.hypot(point[0] - points[0][0], point[1] - points[0][1]);
        for (let i = 0; i < (closed ? n : n - 1); i++) {
            best = Math.min(best, distanceToSegment(point, points[i], points[(i + 1) % n]));
        }
        return best;
    }

    /* Indices of every polygon under the point, topmost first: polygons
       containing it, plus polygons whose edge is within a few screen pixels
       (so thin or tiny polygons can still be picked). */
    function polygonsAt(point) {
        const tolerance = EDGE_HIT_SCREEN_PX / view.scale;
        const hits = [];
        for (let i = polygons.length - 1; i >= 0; i--) {
            const pts = polygons[i].points;
            if (pointInPolygon(point, pts) || distanceToRing(point, pts, true) <= tolerance) hits.push(i);
        }
        return hits;
    }

    function topPolygonAt(point) {
        const hits = polygonsAt(point);
        return hits.length ? hits[0] : -1;
    }

    function draftAt(point) {
        if (!currentPoints.length) return false;
        return distanceToRing(point, currentPoints, false) <= (EDGE_HIT_SCREEN_PX + 2) / view.scale;
    }

    function resetDraft() {
        currentPoints = [];
        hoverPoint = null;
        if (eraseTarget && eraseTarget.type === "draft") eraseTarget = null;
    }

    function cancelDraft() {
        if (!currentPoints.length) return false;
        const count = currentPoints.length;
        resetDraft();
        redraw();
        setStatus(`Unfinished drawing removed (${count} point${count === 1 ? "" : "s"}). Finished polygons were not touched.`);
        return true;
    }

    function deletePolygon(index) {
        if (index < 0 || index >= polygons.length) return;
        const entry = classById(polygons[index].class_id);
        snapshot();
        polygons.splice(index, 1); // exactly this one polygon
        selectedIndex = -1;
        eraseTarget = null;
        dragVertex = null;
        markDirty();
        refreshLists();
        redraw();
        setStatus(`Deleted polygon #${index + 1} (${entry ? entry.label : "?"}). Ctrl+Z to undo. Save again to update the masks.`);
    }

    function changeSelectedClass(classId) {
        if (selectedIndex < 0 || !polygons[selectedIndex] || polygons[selectedIndex].class_id === classId) return;
        snapshot();
        polygons[selectedIndex].class_id = classId;
        markDirty();
        refreshLists();
        redraw();
        setStatus(`Polygon #${selectedIndex + 1} changed to "${classById(classId).label}".`);
    }

    // ---------------- Floating context bar (selection / draft) ----------------
    function updateContextBar() {
        const bar = $("context-bar");
        if (!bar) return;
        let html = "";
        if (tool === "select" && selectedIndex >= 0 && polygons[selectedIndex]) {
            const polygon = polygons[selectedIndex];
            const entry = classById(polygon.class_id) || { label: "?", color: "#fff" };
            const active = classById(activeClassId);
            html =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<strong>#${selectedIndex + 1} ${escapeHtml(entry.label)}</strong>` +
                `<span class="ctx-meta">${polygon.points.length} pts ${formatArea(polygonAreaM2(polygon))}</span>` +
                (active && active.id !== polygon.class_id
                    ? `<button type="button" class="btn btn-sm" data-ctx="reclass">Change to ${escapeHtml(active.label)}</button>` : "") +
                `<button type="button" class="btn btn-sm btn-danger" data-ctx="delete">Delete <span class="kbd">Del</span></button>` +
                `<button type="button" class="btn btn-sm btn-ghost" data-ctx="deselect">Deselect</button>`;
        } else if (stroke) {
            const entry = classById(activeClassId) || { label: "?", color: "#fff" };
            html =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<strong>Drawing ${escapeHtml(entry.label)}</strong>` +
                `<span class="ctx-meta">release to close the shape · Esc to cancel</span>`;
        } else if (tool === "freehand" && !currentPoints.length) {
            const entry = classById(activeClassId) || { label: "?", color: "#fff" };
            html =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<strong>Freehand ${escapeHtml(entry.label)}</strong>` +
                `<span class="ctx-meta">press and hold, draw around the area, release to close it</span>`;
        } else if (currentPoints.length) {
            const entry = classById(activeClassId) || { label: "?", color: "#fff" };
            html =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<strong>Unfinished ${escapeHtml(entry.label)}</strong>` +
                `<span class="ctx-meta">${currentPoints.length} point${currentPoints.length === 1 ? "" : "s"}</span>` +
                (currentPoints.length >= 3 ? `<button type="button" class="btn btn-sm" data-ctx="finish">Finish <span class="kbd">Enter</span></button>` : "") +
                `<button type="button" class="btn btn-sm btn-ghost" data-ctx="undo-point">Remove last point <span class="kbd">⌫</span></button>` +
                `<button type="button" class="btn btn-sm btn-danger" data-ctx="cancel">Cancel drawing <span class="kbd">Esc</span></button>`;
        } else if (tool === "erase") {
            html = `<strong>Erase</strong><span class="ctx-meta">Hover a polygon or an unfinished drawing -- it turns red -- then click to delete only that.</span>`;
        } else if (tool === "select") {
            html = `<strong>Select</strong><span class="ctx-meta">Click a polygon to select it. Click again on overlapping polygons to cycle.</span>`;
        } else if (tool === "draw") {
            const entry = classById(activeClassId) || { label: "?", color: "#fff" };
            html =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<strong>Points ${escapeHtml(entry.label)}</strong>` +
                `<span class="ctx-meta">click to add points, click the first point or press Enter to close</span>`;
        }
        // Pan hint only for the idle hints (no buttons), to keep the strip short.
        if (html && !html.includes("data-ctx")) html += `<span class="ctx-meta ctx-pan-hint">· drag the empty space to move the image, double-click it to centre</span>`;
        // The strip always keeps its height (only its content changes), so
        // the image area never resizes underneath the user.
        if (!baseImage) html = "";
        if (bar.dataset.html !== html) {
            bar.innerHTML = html;
            bar.dataset.html = html;
        }
    }

    $("context-bar").addEventListener("mousedown", (event) => event.stopPropagation());
    $("context-bar").addEventListener("click", function (event) {
        const button = event.target.closest("[data-ctx]");
        if (!button) return;
        const action = button.dataset.ctx;
        if (action === "delete") deletePolygon(selectedIndex);
        else if (action === "deselect") { selectedIndex = -1; refreshLists(); redraw(); }
        else if (action === "reclass") changeSelectedClass(activeClassId);
        else if (action === "finish") closeCurrentPolygon();
        else if (action === "cancel") cancelDraft();
        else if (action === "undo-point") { currentPoints.pop(); if (!currentPoints.length) hoverPoint = null; redraw(); }
    });

    function polygonAreaPx(points) {
        let sum = 0;
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) sum += (points[j][0] + points[i][0]) * (points[j][1] - points[i][1]);
        return Math.abs(sum / 2);
    }

    function polygonAreaM2(polygon) {
        if (!canGeoreference(currentMode)) return null;
        const ll = polygon.points.map((p) => toLonLat(p, currentMode));
        const lat0 = ll.reduce((s, p) => s + p[1], 0) / ll.length;
        const mx = 111320 * Math.cos((lat0 * Math.PI) / 180);
        return polygonAreaPx(ll.map(([lon, lat]) => [lon * mx, lat * 110574]));
    }

    function formatArea(m2) {
        if (m2 == null) return "";
        return m2 >= 10000 ? `${(m2 / 10000).toFixed(2)} ha` : `${Math.round(m2)} m²`;
    }

    // ---------------- Sidebar lists ----------------
    function renderClassGrid() {
        const grid = $("class-grid");
        grid.innerHTML = "";
        const counts = {};
        polygons.forEach((p) => { counts[p.class_id] = (counts[p.class_id] || 0) + 1; });
        labelClasses.forEach((entry, index) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "class-btn" + (entry.id === activeClassId ? " active" : "");
            btn.title = `${entry.label} (key ${(index + 1) % 10})`;
            btn.innerHTML =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<span class="class-name">${escapeHtml(entry.label)}</span>` +
                (counts[entry.id] ? `<span class="class-count-pill">${counts[entry.id]}</span>` : "") +
                `<span class="class-key">${(index + 1) % 10}</span>`;
            btn.addEventListener("click", () => setActiveClass(entry.id));
            grid.appendChild(btn);
        });
    }

    function setActiveClass(id) {
        // Only sets the class for NEW polygons. A selected polygon is never
        // changed implicitly -- use "Change to …" in the selection bar.
        activeClassId = id;
        refreshLists();
        redraw();
    }

    function renderPolygonList() {
        const list = $("polygon-list");
        $("polygon-total").textContent = String(polygons.length);
        if (!polygons.length) {
            list.innerHTML = '<div class="empty-note">No polygons yet. Pick a class and click on the image.</div>';
            return;
        }
        list.innerHTML = "";
        polygons.forEach((polygon, index) => {
            const entry = classById(polygon.class_id) || { label: "?", color: "#fff" };
            const item = document.createElement("div");
            item.className = "polygon-item" + (index === selectedIndex ? " selected" : "");
            item.innerHTML =
                `<span class="class-swatch" style="background:${entry.color}"></span>` +
                `<span class="polygon-label">#${index + 1} ${escapeHtml(entry.label)} <span class="polygon-meta">· ${polygon.points.length} pts ${formatArea(polygonAreaM2(polygon))}</span></span>` +
                `<button type="button" class="icon-btn" title="Delete polygon">✕</button>`;
            item.querySelector(".polygon-label").addEventListener("click", () => {
                setTool("select");
                selectedIndex = index;
                centerOnPolygon(polygon);
                refreshLists();
            });
            item.querySelector(".icon-btn").addEventListener("click", () => deletePolygon(index));
            list.appendChild(item);
        });
    }

    function centerOnPolygon(polygon) {
        const xs = polygon.points.map((p) => p[0]);
        const ys = polygon.points.map((p) => p[1]);
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
        const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        view.offsetX = viewport.clientWidth / 2 - cx * view.scale;
        view.offsetY = viewport.clientHeight / 2 - cy * view.scale;
        redraw();
    }

    function refreshLists() {
        renderClassGrid();
        renderPolygonList();
    }

    // ---------------- Tools ----------------
    function setTool(name) {
        // Tools are independent: switching never deletes anything. An
        // unfinished drawing stays (dashed) until it is finished, cancelled
        // (Esc / Cancel drawing) or erased; returning to Draw continues it.
        tool = name;
        hoverPoint = null;
        eraseTarget = null;
        dragVertex = null;
        stroke = null;
        pendingTap = null;
        if (name !== "select") selectedIndex = -1;
        document.querySelectorAll("#tool-modes [data-tool]").forEach((btn) => btn.classList.toggle("active", btn.dataset.tool === name));
        viewport.classList.toggle("mode-select", name === "select");
        viewport.classList.toggle("mode-erase", name === "erase");
        viewport.classList.toggle("mode-freehand", name === "freehand");
        refreshLists();
        redraw();
        setStatus({
            draw: currentPoints.length
                ? "Draw: continuing your unfinished polygon. Click the first point or press Enter to close, Esc to cancel."
                : "Draw: click to add points, click the first point (or press Enter) to close.",
            freehand: "Freehand: press and hold (mouse, finger or pen), draw around the area, release to close it.",
            select: "Select: click a polygon to select it, drag its square handles to adjust, Del to delete it.",
            erase: "Erase: hover a polygon or unfinished drawing (it turns red), then click to delete only that."
        }[name]);
    }

    document.querySelectorAll("#tool-modes [data-tool]").forEach((btn) => btn.addEventListener("click", () => setTool(btn.dataset.tool)));

    // ---------------- Pointer input ----------------
    canvas.addEventListener("contextmenu", (event) => event.preventDefault());

    function clampToImage(point) {
        return [Math.min(Math.max(point[0], 0), surfaceSize.width), Math.min(Math.max(point[1], 0), surfaceSize.height)];
    }

    function eraseTargetAt(point) {
        // The unfinished drawing wins when the cursor is on it, so it can
        // always be removed without touching a finished polygon underneath.
        if (draftAt(point)) return { type: "draft" };
        const index = topPolygonAt(point);
        return index === -1 ? null : { type: "polygon", index };
    }

    /* Click / tap action of the Draw (points), Select and Erase tools. */
    function primaryAction(clientX, clientY) {
        const point = screenToImage(clientX, clientY);

        if (tool === "select") {
            const hits = polygonsAt(point);
            if (!hits.length) {
                selectedIndex = -1;
            } else {
                // Clicking again where polygons overlap cycles through them.
                const position = hits.indexOf(selectedIndex);
                selectedIndex = position === -1 ? hits[0] : hits[(position + 1) % hits.length];
            }
            refreshLists();
            redraw();
            if (selectedIndex >= 0) {
                const entry = classById(polygons[selectedIndex].class_id);
                setStatus(`Selected polygon #${selectedIndex + 1} (${entry ? entry.label : "?"})` +
                    (hits.length > 1 ? ` -- ${hits.length} polygons overlap here, click again to cycle.` : "."));
            } else {
                setStatus("Nothing selected.");
            }
            return;
        }

        if (tool === "erase") {
            const target = eraseTargetAt(point);
            if (!target) {
                setStatus("Nothing to erase here.");
            } else if (target.type === "draft") {
                cancelDraft();
            } else {
                deletePolygon(target.index);
            }
            eraseTarget = eraseTargetAt(point);
            redraw();
            return;
        }

        if (tool !== "draw") return;
        // Ignore the second click of a fast double-click that closed a
        // polygon, so it cannot start a stray one-point drawing.
        if (!currentPoints.length && lastClose && performance.now() - lastClose.time < 400 &&
            Math.hypot(point[0] - lastClose.x, point[1] - lastClose.y) * view.scale < 8) {
            lastClose = null;
            return;
        }
        if (currentPoints.length >= 3) {
            const first = currentPoints[0];
            if (Math.hypot(first[0] - point[0], first[1] - point[1]) * view.scale <= CLOSE_RADIUS_SCREEN_PX) {
                closeCurrentPolygon(point);
                return;
            }
        }
        if (!currentPoints.length) {
            selectedIndex = -1;
            lastClose = null;
        }
        const clamped = clampToImage(point);
        currentPoints.push(clamped);
        hoverPoint = clamped; // the preview starts at the new point itself -- never at an old position
        redraw();
    }

    // ---- Two-finger pan / pinch-zoom (tablets, phones) ----
    function touchCenterAndDistance() {
        const [a, b] = [...activeTouches.values()];
        const rect = canvas.getBoundingClientRect();
        return {
            x: (a.x + b.x) / 2 - rect.left,
            y: (a.y + b.y) / 2 - rect.top,
            distance: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y))
        };
    }

    function startGesture() {
        // Two fingers = navigate. Anything the first finger started is undone.
        if (stroke && stroke.pointerType === "touch") stroke = null;
        pendingTap = null;
        dragVertex = null;
        panState = null;
        viewport.classList.remove("panning");
        const c = touchCenterAndDistance();
        gesture = { scale: view.scale, offsetX: view.offsetX, offsetY: view.offsetY, x: c.x, y: c.y, distance: c.distance };
        redraw();
    }

    function updateGesture() {
        const c = touchCenterAndDistance();
        const newScale = Math.max(MIN_SCALE, Math.min(gesture.scale * (c.distance / gesture.distance), MAX_SCALE));
        // Keep the image point that was under the fingers' midpoint under it.
        const ix = (gesture.x - gesture.offsetX) / gesture.scale;
        const iy = (gesture.y - gesture.offsetY) / gesture.scale;
        view.scale = newScale;
        view.offsetX = c.x - ix * newScale;
        view.offsetY = c.y - iy * newScale;
        redraw();
    }

    // The empty space around the image is for moving the view: a press
    // there pans (any tool, mouse/finger/pen), a double-click centres.
    // A few screen pixels around the edge still count as the image, so a
    // point can be placed right on the border.
    const IMAGE_EDGE_MARGIN_SCREEN_PX = 6;

    function isOnImage(point) {
        if (!surfaceSize) return false;
        const margin = IMAGE_EDGE_MARGIN_SCREEN_PX / view.scale;
        return point[0] >= -margin && point[1] >= -margin &&
            point[0] <= surfaceSize.width + margin && point[1] <= surfaceSize.height + margin;
    }

    function startPan(event) {
        panState = { x: event.clientX, y: event.clientY, ox: view.offsetX, oy: view.offsetY, pointerId: event.pointerId };
        viewport.classList.add("panning");
        hoverPoint = null;
        try { canvas.setPointerCapture(event.pointerId); } catch (e) { /* not capturable */ }
    }

    canvas.addEventListener("pointerdown", function (event) {
        if (!baseImage) return;

        if (event.pointerType === "touch") {
            activeTouches.set(event.pointerId, { x: event.clientX, y: event.clientY });
            // Palm rejection: while a pen is drawing, ignore the hand.
            if (stroke && stroke.pointerType === "pen") return;
            if (activeTouches.size >= 2) {
                event.preventDefault();
                startGesture();
                return;
            }
        }
        if (gesture) return;
        if (stroke && event.pointerId !== stroke.pointerId) return; // one stroke at a time

        if (event.button === 1 || event.button === 2 || spaceHeld) {
            startPan(event);
            event.preventDefault();
            return;
        }
        if (event.button !== 0) return;
        const point = screenToImage(event.clientX, event.clientY);
        if (!isOnImage(point)) {
            startPan(event);
            event.preventDefault();
            return;
        }

        // Dragging a handle of the selected polygon (mouse, pen or finger).
        if (tool === "select" && selectedIndex >= 0 && polygons[selectedIndex]) {
            const tolerance = (event.pointerType === "touch" ? VERTEX_HIT_SCREEN_PX * 2 : VERTEX_HIT_SCREEN_PX) / view.scale;
            const vertex = polygons[selectedIndex].points.findIndex((p) => Math.hypot(p[0] - point[0], p[1] - point[1]) <= tolerance);
            if (vertex !== -1) {
                // A drag only starts after the pointer really moves, so a
                // plain click on a handle never alters the geometry.
                dragVertex = { polygon: selectedIndex, vertex, startX: event.clientX, startY: event.clientY, active: false, pointerId: event.pointerId };
                return;
            }
        }

        if (tool === "freehand") {
            event.preventDefault();
            selectedIndex = -1;
            stroke = { pointerId: event.pointerId, pointerType: event.pointerType, points: [clampToImage(point)] };
            try { canvas.setPointerCapture(event.pointerId); } catch (e) { /* not capturable */ }
            redraw();
            return;
        }

        if (event.pointerType === "touch") {
            // Confirmed on lift, so the first finger of a pinch does nothing.
            pendingTap = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
            return;
        }
        primaryAction(event.clientX, event.clientY);
    });

    window.addEventListener("pointermove", function (event) {
        if (event.pointerType === "touch" && activeTouches.has(event.pointerId)) {
            activeTouches.set(event.pointerId, { x: event.clientX, y: event.clientY });
            if (gesture && activeTouches.size >= 2) {
                updateGesture();
                return;
            }
        }
        if (gesture) return;
        if (panState) {
            view.offsetX = panState.ox + (event.clientX - panState.x);
            view.offsetY = panState.oy + (event.clientY - panState.y);
            redraw();
            return;
        }
        if (!baseImage) return;

        if (stroke && event.pointerId === stroke.pointerId) {
            // Coalesced events keep pen strokes smooth at high sampling rates.
            const samples = typeof event.getCoalescedEvents === "function" ? event.getCoalescedEvents() : [];
            let added = false;
            (samples.length ? samples : [event]).forEach((sample) => { added = addStrokePoint(sample.clientX, sample.clientY) || added; });
            if (added) redraw();
            return;
        }
        if (pendingTap && event.pointerId === pendingTap.pointerId &&
            Math.hypot(event.clientX - pendingTap.x, event.clientY - pendingTap.y) > TAP_MAX_MOVE_SCREEN_PX) {
            pendingTap = null; // a swipe, not a tap
        }

        const rect = canvas.getBoundingClientRect();
        const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
        const point = screenToImage(event.clientX, event.clientY);
        viewport.classList.toggle("over-empty", inside && !isOnImage(point) && !dragVertex);

        if (dragVertex && (dragVertex.pointerId === undefined || dragVertex.pointerId === event.pointerId)) {
            if (!dragVertex.active) {
                if (Math.hypot(event.clientX - dragVertex.startX, event.clientY - dragVertex.startY) < DRAG_THRESHOLD_SCREEN_PX) return;
                snapshot();
                dragVertex.active = true;
            }
            const polygon = polygons[dragVertex.polygon];
            if (polygon) {
                polygon.points[dragVertex.vertex] = clampToImage(point);
                markDirty();
            }
            redraw();
            return;
        }

        if (inside) {
            const onImage = point[0] >= 0 && point[1] >= 0 && point[0] <= surfaceSize.width && point[1] <= surfaceSize.height;
            if (onImage && canGeoreference(currentMode)) {
                const [lon, lat] = toLonLat(point, currentMode);
                $("status-coords").textContent = `${lat.toFixed(6)}°N  ${lon.toFixed(6)}°E`;
            } else {
                $("status-coords").textContent = onImage ? `x ${point[0].toFixed(0)}, y ${point[1].toFixed(0)}` : "";
            }
        }

        if (tool === "draw" && currentPoints.length && event.pointerType !== "touch") {
            hoverPoint = inside && isOnImage(point) ? clampToImage(point) : null;
            redraw();
        } else if (tool === "erase" && event.pointerType !== "touch") {
            const target = inside ? eraseTargetAt(point) : null;
            if (JSON.stringify(target) !== JSON.stringify(eraseTarget)) {
                eraseTarget = target;
                redraw();
            }
        }
    });

    function endPointer(event, cancelled) {
        if (event.pointerType === "touch") {
            activeTouches.delete(event.pointerId);
            if (gesture) {
                if (activeTouches.size < 2) gesture = null;
                pendingTap = null;
                return;
            }
        }
        if (panState) {
            panState = null;
            viewport.classList.remove("panning");
        }
        if (stroke && event.pointerId === stroke.pointerId) {
            if (cancelled) {
                cancelStroke();
                setStatus("Stroke cancelled.");
            } else {
                finishStroke();
            }
            return;
        }
        if (pendingTap && event.pointerId === pendingTap.pointerId) {
            const tap = pendingTap;
            pendingTap = null;
            if (!cancelled) primaryAction(tap.x, tap.y);
            return;
        }
        if (dragVertex) {
            const moved = dragVertex.active;
            dragVertex = null;
            if (moved) {
                refreshLists();
                setStatus("Point moved. Ctrl+Z to undo.");
            }
            redraw();
        }
    }

    window.addEventListener("pointerup", (event) => endPointer(event, false));
    window.addEventListener("pointercancel", (event) => endPointer(event, true));

    canvas.addEventListener("pointerleave", function () {
        if (hoverPoint || eraseTarget) {
            hoverPoint = null;
            eraseTarget = null;
            redraw();
        }
    });

    canvas.addEventListener("dblclick", function (event) {
        event.preventDefault();
        if (baseImage && !isOnImage(screenToImage(event.clientX, event.clientY))) {
            fitToScreen();
            setStatus("Image centred.");
            return;
        }
        if (tool !== "draw" || !currentPoints.length) return;
        // Both clicks of the double-click added a point at the same spot;
        // drop the duplicate before closing.
        if (currentPoints.length >= 2) {
            const a = currentPoints[currentPoints.length - 1];
            const b = currentPoints[currentPoints.length - 2];
            if (Math.hypot(a[0] - b[0], a[1] - b[1]) * view.scale < 4) currentPoints.pop();
        }
        if (currentPoints.length >= 3) closeCurrentPolygon(screenToImage(event.clientX, event.clientY));
    });

    canvas.addEventListener("wheel", function (event) {
        event.preventDefault();
        zoomAt(event.deltaY < 0 ? 1.2 : 1 / 1.2, event.clientX, event.clientY);
    }, { passive: false });

    window.addEventListener("keydown", function (event) {
        const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
        if (typing) return;
        if (event.code === "Space") {
            spaceHeld = true;
            event.preventDefault();
            return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); undo(); return; }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") { event.preventDefault(); redo(); return; }
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === "Enter" && currentPoints.length) { event.preventDefault(); closeCurrentPolygon(); return; }
        if (event.key === "Escape") {
            // Esc cancels a freehand stroke or an unfinished drawing first;
            // otherwise it deselects.
            if (cancelStroke()) {
                setStatus("Stroke cancelled.");
            } else if (!cancelDraft() && selectedIndex >= 0) {
                selectedIndex = -1;
                refreshLists();
                redraw();
                setStatus("Nothing selected.");
            }
            return;
        }
        if (event.key === "Backspace" && currentPoints.length && tool === "draw") {
            event.preventDefault();
            currentPoints.pop();
            if (!currentPoints.length) hoverPoint = null;
            redraw();
            return;
        }
        if (event.key === "Delete" || event.key === "Backspace") {
            event.preventDefault();
            if (tool === "select" && selectedIndex >= 0) deletePolygon(selectedIndex);
            else if (currentPoints.length) cancelDraft();
            return;
        }
        if (/^[0-9]$/.test(event.key)) {
            const index = event.key === "0" ? 9 : Number(event.key) - 1;
            if (labelClasses[index]) setActiveClass(labelClasses[index].id);
            return;
        }
        const key = event.key.toLowerCase();
        if (key === "d") setTool("draw");
        else if (key === "b") setTool("freehand");
        else if (key === "s") setTool("select");
        else if (key === "e") setTool("erase");
        else if (key === "f") fitToScreen();
        else if (key === "+" || key === "=") zoomAt(1.25);
        else if (key === "-") zoomAt(1 / 1.25);
    });

    window.addEventListener("keyup", (event) => { if (event.code === "Space") spaceHeld = false; });

    // ---------------- Toolbar ----------------
    $("undo-btn").addEventListener("click", undo);
    $("redo-btn").addEventListener("click", redo);
    $("clear-btn").addEventListener("click", function () {
        if (!polygons.length && !currentPoints.length) return;
        if (!confirm("Delete all polygons? (You can undo this.)")) return;
        snapshot();
        polygons = [];
        resetDraft();
        selectedIndex = -1;
        eraseTarget = null;
        markDirty();
        refreshLists();
        redraw();
    });
    $("zoom-in-btn").addEventListener("click", () => zoomAt(1.25));
    $("zoom-out-btn").addEventListener("click", () => zoomAt(1 / 1.25));
    $("fit-screen-btn").addEventListener("click", fitToScreen);
    $("reset-view-btn").addEventListener("click", function () {
        if (!surfaceSize) return;
        const rect = canvas.getBoundingClientRect();
        zoomAt(1 / view.scale, rect.left + rect.width / 2, rect.top + rect.height / 2);
    });
    $("fill-opacity").addEventListener("input", function () {
        fillOpacity = Number(this.value);
        redraw();
    });
    $("toggle-polygons-btn").addEventListener("click", function () {
        polygonsVisible = !polygonsVisible;
        this.textContent = polygonsVisible ? "Hide labels" : "Show labels";
        this.classList.toggle("active", !polygonsVisible);
        redraw();
    });
    $("toggle-aoi-btn").addEventListener("click", function () {
        aoiVisible = !aoiVisible;
        this.classList.toggle("active", aoiVisible);
        redraw();
    });

    const app = $("label-app");
    $("label-fullscreen-btn").addEventListener("click", function () {
        if (!document.fullscreenElement) (app.requestFullscreen || app.webkitRequestFullscreen).call(app);
        else document.exitFullscreen();
    });
    document.addEventListener("fullscreenchange", function () {
        $("label-fullscreen-btn").textContent = document.fullscreenElement ? "✕" : "⛶";
        $("label-fullscreen-btn").title = document.fullscreenElement ? "Exit fullscreen" : "Fullscreen";
    });

    new ResizeObserver(() => {
        const hadImage = Boolean(surfaceSize);
        resizeCanvas();
        if (hadImage && !panState) redraw();
    }).observe(viewport);

    // ---------------- Surfaces ----------------
    function surfaceUrl(mode) {
        if (mode === "screenshot") return selectData.reference_url;
        return selectData.preview_urls && selectData.preview_urls[mode];
    }

    function surfaceDims(mode) {
        if (mode === "screenshot") return { width: selectData.reference_info.width, height: selectData.reference_info.height };
        return { width: selectData.preview_info.width, height: selectData.preview_info.height };
    }

    function updateSurfaceButtons() {
        document.querySelectorAll("#surface-switch [data-mode]").forEach((btn) => {
            const mode = btn.dataset.mode;
            const available = Boolean(selectData) && Boolean(mode === "screenshot" ? selectData.screenshot_ready : surfaceUrl(mode));
            btn.disabled = !available;
            btn.classList.toggle("active", mode === currentMode);
        });
    }

    function loadImage(url) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error("image failed to load"));
            image.src = `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`;
        });
    }

    async function switchSurface(mode, keepView) {
        if (!selectData || mode === currentMode && baseImage) return;
        const url = surfaceUrl(mode);
        if (!url) return;
        setStatus("Loading image…");
        let image;
        try {
            image = await loadImage(url);
        } catch (error) {
            setStatus("Could not load that image. Staying on the current one.", true);
            return;
        }
        const previousMode = currentMode;
        const sameGrid = previousMode !== "screenshot" && mode !== "screenshot";
        const previousSize = surfaceSize;

        if (baseImage && !sameGrid && (polygons.length || currentPoints.length)) {
            if (canGeoreference(previousMode) && canGeoreference(mode)) {
                const convert = (points) => points.map((p) => fromLonLat(toLonLat(p, previousMode), mode));
                polygons = polygons.map((p) => ({ class_id: p.class_id, points: convert(p.points) }));
                currentPoints = convert(currentPoints);
                hoverPoint = null;
                undoStack = [];
                redoStack = [];
            } else {
                polygons = [];
                resetDraft();
                setStatus("This GeoTIFF is not in EPSG:4326, so polygons could not be carried over.", true);
            }
        }

        // Keep the same ground area in view when switching between grids.
        let center = null;
        if (keepView && previousSize && canGeoreference(previousMode) && canGeoreference(mode)) {
            const cx = (viewport.clientWidth / 2 - view.offsetX) / view.scale;
            const cy = (viewport.clientHeight / 2 - view.offsetY) / view.scale;
            center = { lonlat: toLonLat([cx, cy], previousMode), groundPerScreenPx: null };
            const a = toLonLat([cx, cy], previousMode);
            const b = toLonLat([cx + 1 / view.scale, cy], previousMode);
            center.groundPerScreenPx = Math.abs(b[0] - a[0]);
        }

        currentMode = mode;
        baseImage = image;
        surfaceSize = surfaceDims(mode);
        selectedIndex = -1;
        updateSurfaceButtons();

        if (center) {
            const p0 = fromLonLat(center.lonlat, mode);
            const p1 = fromLonLat([center.lonlat[0] + center.groundPerScreenPx, center.lonlat[1]], mode);
            view.scale = Math.max(MIN_SCALE, Math.min(Math.abs(p1[0] - p0[0]), MAX_SCALE));
            view.offsetX = viewport.clientWidth / 2 - p0[0] * view.scale;
            view.offsetY = viewport.clientHeight / 2 - p0[1] * view.scale;
            redraw();
        } else {
            fitToScreen();
        }
        $("canvas-empty").hidden = true;
        $("status-image").textContent = `${surfaceSize.width}×${surfaceSize.height} px`;
        refreshLists();
        setStatus(mode === "screenshot"
            ? "Drawing on the high-resolution screenshot."
            : `Drawing on the GeoTIFF ${mode === "rgb" ? "True RGB" : mode === "ndvi" ? "NDVI" : "SAR false-color"} preview (10 m pixels).`);
    }

    document.querySelectorAll("#surface-switch [data-mode]").forEach((btn) => {
        btn.addEventListener("click", () => switchSurface(btn.dataset.mode, true));
    });

    // ---------------- Job loading ----------------
    async function loadJobList(preselect) {
        const select = $("job-select");
        try {
            const data = await (await fetch("/historical/jobs")).json();
            const usable = (data.jobs || []).filter((job) => job.screenshot_ready || job.ready_years.length);
            select.innerHTML = usable.length ? '<option value="">Choose an area…</option>' : '<option value="">No collected areas yet</option>';
            usable.forEach((job) => {
                const option = document.createElement("option");
                option.value = job.job_id;
                const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : "";
                const years = job.years.length > 1 ? ` (${job.years[0]}–${job.years[job.years.length - 1]})` : "";
                option.textContent = `${job.area_name}${years} · ${date}${job.mask_saved ? " · labeled" : ""}`;
                select.appendChild(option);
            });
            if (preselect && usable.some((job) => job.job_id === preselect)) {
                select.value = preselect;
                await loadJob(preselect);
            } else if (preselect) {
                setStatus("That job has no screenshot or GeoTIFF ready yet.", true);
            } else if (jobId) {
                select.value = jobId;
            }
        } catch (error) {
            select.innerHTML = '<option value="">Could not load areas</option>';
        }
    }

    $("job-select").addEventListener("change", function () {
        if (dirty && !confirm("You have unsaved polygons. Switch area anyway?")) {
            this.value = jobId || "";
            return;
        }
        if (this.value) loadJob(this.value);
    });

    $("year-select").addEventListener("change", function () {
        if (dirty && !confirm("You have unsaved polygons. Switch year anyway?")) {
            this.value = year;
            return;
        }
        selectYear(this.value);
    });

    async function loadJob(id) {
        const data = await (await fetch(`/historical/status/${id}`)).json();
        if (!data.success) {
            setStatus(data.message || "Job not found.", true);
            return;
        }
        jobId = id;
        history.replaceState(null, "", `/labeling?job_id=${id}`);
        $("nav-collect-link").href = `/historical?job_id=${id}`;
        const job = data.job;
        const years = Object.keys(job.years).sort();
        const readyYears = years.filter((y) => job.years[y].file_path && ["READY", "DOWNLOADED"].includes(job.years[y].state));
        const yearSelect = $("year-select");
        yearSelect.innerHTML = "";
        (readyYears.length ? readyYears : years).forEach((y) => {
            const option = document.createElement("option");
            option.value = y;
            option.textContent = y;
            yearSelect.appendChild(option);
        });
        const preferred = job.labeling && job.labeling.year && readyYears.includes(String(job.labeling.year))
            ? String(job.labeling.year)
            : (readyYears.includes("2025") ? "2025" : (readyYears[readyYears.length - 1] || years[years.length - 1]));
        yearSelect.value = preferred;
        $("year-row").hidden = years.length <= 1;
        await selectYear(preferred);
    }

    async function selectYear(selectedYear) {
        setStatus("Loading…");
        let data;
        try {
            const response = await fetch("/labeling/select-year", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: jobId, year: selectedYear })
            });
            data = await response.json();
        } catch (error) {
            setStatus(`Network error: ${error}`, true);
            return;
        }
        if (!data.success) {
            setStatus(data.message || "Could not load this area.", true);
            return;
        }

        selectData = data;
        year = String(data.year);
        labelClasses = data.label_classes;
        if (!classById(activeClassId)) activeClassId = labelClasses[0].id;
        polygons = [];
        resetDraft();
        eraseTarget = null;
        lastClose = null;
        dragVertex = null;
        undoStack = [];
        redoStack = [];
        selectedIndex = -1;
        baseImage = null;
        dirty = false;
        $("save-result").hidden = true;
        $("save-warning-panel").hidden = true;
        const savedStats = data.labeling && String(data.labeling.year) === String(data.year) ? data.labeling.area_stats : null;
        renderAreaStats(savedStats);

        renderDatasetInfo(data);
        const link = $("download-dataset-link");
        link.href = `/historical/download-zip/${jobId}`;
        link.classList.remove("is-disabled");
        $("drive-save-btn").disabled = !driveConfigured;

        const startMode = data.screenshot_ready ? "screenshot" : (data.preview_urls ? "rgb" : null);
        if (!startMode) {
            setStatus(data.preview_error || "No image is available to draw on for this area.", true);
            return;
        }
        currentMode = startMode;
        await switchSurface(startMode, false);

        if (data.saved_polygons && data.saved_polygons.length) {
            polygons = data.saved_polygons.map((p) => ({
                class_id: p.class_id,
                points: currentMode === "screenshot" ? p.points : p.points.map((pt) => fromLonLat(screenshotToLonLat(pt), currentMode))
            }));
            setStatus(`Loaded ${polygons.length} previously saved polygon(s). Edit them and save again, or keep drawing.`);
        } else if (data.preview_error) {
            setStatus(data.preview_error, true);
        }
        updateSaveButton();
        refreshLists();
        redraw();
    }

    function renderDatasetInfo(data) {
        const rows = [["Area", data.job.area_name], ["Year", `February ${data.year}`]];
        if (data.screenshot_ready) {
            const info = data.reference_info;
            rows.push(["Screenshot", `${info.width}×${info.height} px` + (info.ground_resolution_m ? ` · ${info.ground_resolution_m.toFixed(2)} m/px` : ` · zoom ${info.zoom}`)]);
        } else {
            rows.push(["Screenshot", "not available"]);
        }
        rows.push(["GeoTIFF", data.geotiff ? `${data.geotiff.width}×${data.geotiff.height} px · 10 m` : "not available"]);
        if (data.labeling && data.labeling.saved_at) {
            rows.push(["Last saved", `${new Date(data.labeling.saved_at).toLocaleString()} · ${data.labeling.polygon_count} polygons`]);
        }
        $("dataset-kv").innerHTML = rows.map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`).join("");
        $("dataset-info").hidden = false;
    }

    // ---------------- Area statistics ----------------
    const OPTION_KEYS = { band: "labelBorderBandM", other: "labelFillOther" };
    try {
        const savedBand = localStorage.getItem(OPTION_KEYS.band);
        if (savedBand !== null && savedBand !== "") $("border-band-input").value = savedBand;
        const savedOther = localStorage.getItem(OPTION_KEYS.other);
        if (savedOther !== null) $("fill-other-input").checked = savedOther === "1";
    } catch (e) { /* storage blocked */ }
    $("border-band-input").addEventListener("change", function () {
        this.value = String(borderBandValue());
        try { localStorage.setItem(OPTION_KEYS.band, this.value); } catch (e) { /* storage blocked */ }
    });
    $("fill-other-input").addEventListener("change", function () {
        try { localStorage.setItem(OPTION_KEYS.other, this.checked ? "1" : "0"); } catch (e) { /* storage blocked */ }
    });

    function borderBandValue() {
        const value = Number($("border-band-input").value);
        return Number.isFinite(value) ? Math.max(0, Math.min(value, 20)) : 2;
    }

    function formatM2(m2) {
        if (m2 == null) return "-";
        const rounded = Math.round(m2).toLocaleString();
        return m2 >= 10000 ? `${rounded} m² (${(m2 / 10000).toFixed(2)} ha)` : `${rounded} m²`;
    }

    function formatArea2(m2) {
        // compact form for the sidebar table
        if (m2 == null) return "-";
        return m2 >= 10000 ? `${(m2 / 10000).toFixed(2)} ha` : `${Math.round(m2).toLocaleString()} m²`;
    }

    function formatPct(pct) {
        if (pct == null) return "-";
        return pct > 0 && pct < 0.1 ? "<0.1%" : `${pct.toFixed(1)}%`;
    }

    function renderAreaStats(stats) {
        const section = $("stats-section");
        const grid = stats && stats.primary_grid ? stats[`${stats.primary_grid}_grid`] : null;
        if (!grid) {
            section.hidden = true;
            return;
        }
        // Tree first (the main class of interest), then by area.
        const classes = grid.classes.slice().sort((a, b) =>
            (b.class_key === "forest_tree") - (a.class_key === "forest_tree") || b.area_m2 - a.area_m2);
        const otherLabel = stats.unlabeled_as_other === false ? "Not labeled (ignored)" : "Other / not labeled";

        const bar = classes.map((c) => `<span title="${escapeHtml(c.class_name)} ${formatPct(c.percent)}" style="width:${c.percent}%;background:${c.color}"></span>`).join("") +
            `<span title="Uncertain border" style="width:${grid.uncertain_border.percent}%;background:repeating-linear-gradient(45deg,#64748b 0 3px,transparent 3px 6px)"></span>`;

        const rows = classes.map((c) => {
            const b = c.border;
            const border = b ? `<tr class="stats-sub"><td colspan="3"><div class="stats-border">` +
                `certain ${formatArea2(b.certain_m2)} → <b>est. ${formatArea2(b.estimated_m2)} (${formatPct(b.estimated_percent)})</b> · max ${formatArea2(b.maximum_m2)} · ±${b.uncertainty_percent}%` +
                `</div></td></tr>` : "";
            return `<tr><td><span class="class-swatch" style="background:${c.color}"></span>${escapeHtml(c.class_name)}</td>` +
                `<td class="num">${formatArea2(c.area_m2)}</td><td class="num"><strong>${formatPct(c.percent)}</strong></td></tr>` + border;
        }).join("");

        let comparison = "";
        const tif = stats.geotiff_grid;
        if (stats.primary_grid === "screenshot" && tif) {
            const tree = tif.classes.find((c) => c.class_key === "forest_tree");
            if (tree) {
                comparison = `<div class="stats-note">Same labels on the 10 m GeoTIFF grid: Tree ${formatArea2(tree.area_m2)} (${formatPct(tree.percent)})` +
                    (tree.border ? `, est. ${formatArea2(tree.border.estimated_m2)} using NDVI.` : ".") + `</div>`;
            }
        }

        $("stats-panel").innerHTML =
            `<div class="stats-total"><div><span>Selected area</span><br><strong>${formatM2(stats.aoi_area_m2)}</strong></div>` +
            `<span>${grid.grid === "screenshot" ? "screenshot" : "GeoTIFF"} grid · ${grid.pixel_size_m} m/px</span></div>` +
            `<div class="stats-bar">${bar}</div>` +
            `<table class="stats-table">${rows}` +
            `<tr class="stats-muted"><td>Uncertain border (${stats.border_band_m} m, ignored)</td><td class="num">${formatArea2(grid.uncertain_border.area_m2)}</td><td class="num">${formatPct(grid.uncertain_border.percent)}</td></tr>` +
            `<tr class="stats-muted"><td>${otherLabel}</td><td class="num">${formatArea2(grid.other_unlabeled.area_m2)}</td><td class="num">${formatPct(grid.other_unlabeled.percent)}</td></tr>` +
            `</table>` +
            `<div class="stats-note">Certain = what you drew. Estimated = certain + border pixels that look like that surface in the image (green test for tree/grass/shrub). Saved as <code>labels/…_label_stats.json</code> and <code>.csv</code>.</div>` +
            comparison;
        section.hidden = false;
    }

    // ---------------- Saving ----------------
    async function submitSave(confirmDespiteWarning) {
        const button = $("save-mask-btn");
        button.disabled = true;
        button.textContent = "Saving…";
        setStatus("Saving labels for both models…");
        const payload = lastSavePayload && confirmDespiteWarning ? { ...lastSavePayload, confirm_despite_warning: true } : {
            job_id: jobId,
            year: year,
            polygons: polygons.map((p) => ({ class_id: p.class_id, points: p.points })),
            reference_mode: currentMode,
            confirm_despite_warning: false,
            border_band_m: borderBandValue(),
            fill_unlabeled_as_other: $("fill-other-input").checked
        };
        lastSavePayload = payload;
        try {
            const response = await fetch("/labeling/save-mask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!data.success && data.warning) {
                $("save-warning-text").textContent = data.message;
                $("save-warning-panel").hidden = false;
                setStatus("Check the warning in the sidebar.", true);
                return;
            }
            $("save-warning-panel").hidden = true;
            if (!data.success) {
                setStatus(data.message || "Save failed.", true);
                return;
            }
            dirty = false;
            const outputs = Object.values(data.outputs || {});
            const statsLines = Object.entries(data.quality_stats || {}).map(([grid, s]) =>
                `${grid === "geotiff" ? "GeoTIFF grid" : "Screenshot grid"}: ${s.valid_labeled_pixel_count.toLocaleString()} labeled px of ${s.total_pixels.toLocaleString()}`);
            const result = $("save-result");
            result.innerHTML =
                `<strong>Saved ${data.polygon_count} polygon(s).</strong>` +
                (!data.geotiff_mask_saved ? "<div>GeoTIFF mask skipped -- the GeoTIFF is not available.</div>" : "") +
                (!data.screenshot_mask_saved ? "<div>Screenshot mask skipped -- the screenshot is not available.</div>" : "") +
                `<ul>${statsLines.map((l) => `<li>${escapeHtml(l)}</li>`).join("")}${outputs.map((o) => `<li><code>${escapeHtml(o)}</code></li>`).join("")}</ul>`;
            result.hidden = false;
            renderAreaStats(data.area_stats);
            setStatus(`Saved. Masks written for ${[data.geotiff_mask_saved && "the GeoTIFF model", data.screenshot_mask_saved && "the screenshot model"].filter(Boolean).join(" and ")}.`);
            loadJobList(null);
        } catch (error) {
            setStatus(`Network error while saving: ${error}`, true);
        } finally {
            button.textContent = "Save labels";
            updateSaveButton();
        }
    }

    $("save-mask-btn").addEventListener("click", function () {
        if (!jobId || !selectData) return setStatus("Load an area first.", true);
        if (currentPoints.length) return setStatus("Finish the polygon in progress first (Enter to close, Esc to cancel).", true);
        if (!polygons.length) return setStatus("Draw at least one polygon first.", true);
        lastSavePayload = null;
        submitSave(false);
    });
    $("save-anyway-btn").addEventListener("click", () => submitSave(true));
    $("save-cancel-btn").addEventListener("click", () => { $("save-warning-panel").hidden = true; });

    $("download-dataset-link").addEventListener("click", function (event) {
        if (this.classList.contains("is-disabled")) {
            event.preventDefault();
            return;
        }
        if (dirty && !confirm("You have unsaved polygons -- the ZIP will not include them. Download anyway?")) event.preventDefault();
    });

    window.addEventListener("beforeunload", function (event) {
        if (dirty) {
            event.preventDefault();
            event.returnValue = "";
        }
    });

    // ---------------- Init ----------------
    let driveConfigured = false;
    fetch("/historical/config").then((r) => r.json()).then((config) => {
        if (!labelClasses.length && config.label_classes) {
            labelClasses = config.label_classes;
            activeClassId = labelClasses[0].id;
            refreshLists();
        }
        driveConfigured = Boolean(config.google_client_id);
        window.DriveSave.configure(config.google_client_id);
        window.DriveSave.attachPanel({
            input: $("drive-link-input"),
            button: $("drive-save-btn"),
            status: $("drive-status"),
            getJobId: () => {
                if (dirty && !confirm("You have unsaved polygons -- Drive will get the last SAVED labels. Continue?")) return null;
                return jobId;
            }
        });
        $("drive-save-btn").disabled = !driveConfigured || !jobId;
    }).catch(() => {});

    // Free hosting (e.g. Render free) sleeps after ~15 idle minutes and
    // wipes its scratch disk; a light ping while this page is open keeps
    // the server -- and the job being labeled -- alive.
    setInterval(() => { fetch("/healthz").catch(() => {}); }, 4 * 60 * 1000);

    resizeCanvas();
    loadJobList(new URLSearchParams(window.location.search).get("job_id"));
})();
