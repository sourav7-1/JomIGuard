(() => {
    const $ = (id) => document.getElementById(id);
    const fmt = (n) => Number(n).toLocaleString("en-US");
    const status = (msg, kind = "info") => { const s = $("status"); s.className = `alert alert-${kind}`; s.textContent = msg; s.hidden = !msg; };

    function fill(select, items, label, value) {
        select.innerHTML = items.length ? "" : `<option value="">None available</option>`;
        for (const it of items) {
            const o = document.createElement("option");
            o.value = value(it); o.textContent = label(it);
            select.appendChild(o);
        }
    }

    function modelInfo(m) {
        const el = $("model-info");
        if (!m.segmentation_ready) { el.innerHTML = "<b>No trained model.</b> Run <code>python ai/train_segmentation.py</code>."; return; }
        let html = "";
        const v = m.segmentation && m.segmentation.validation;
        if (v) html += `<b>Land-cover model</b> (held-out areas):<br>pixel accuracy ${(v.pixel_accuracy * 100).toFixed(1)}%, tree IoU ${(v.tree_IoU || 0).toFixed(2)}, mIoU ${v.mIoU.toFixed(2)}<br>`;
        const c = m.counter && m.counter.targets;
        if (c) html += `<b>Tree counter</b> (5-fold CV on ${m.counter.squares} Gazipur squares):<br>` +
            `total trees R² ${c.total_trees.cv.R2}, MAE ±${c.total_trees.cv_count_per_square.MAE} trees per square<br>` +
            `tree cover R² ${c.tree_cover_pct.cv.R2}, MAE ±${c.tree_cover_pct.cv.MAE}%`;
        else html += "<b>Tree counter not trained.</b> Run <code>python ai/train_counter.py</code>.";
        el.innerHTML = html;
    }

    async function loadSources() {
        const d = await (await fetch("/monitor/sources")).json();
        fill($("src-job"), d.jobs, (j) => `${j.area_name} · ${j.year}`, (j) => `${j.job_id}|${j.year}`);
        fill($("src-gaz"), d.gazipur, (g) => `${g.id} · ${g.total_trees} trees counted`, (g) => g.id);
        fill($("src-lab"), d.labelled, (n) => n, (n) => n);
        modelInfo(d.models);
    }

    function show(r) {
        $("result").hidden = false;
        $("r-name").textContent = r.name;
        const c = r.counts;
        $("k-total").textContent = c ? fmt(c.total_trees) : "n/a";
        $("k-split").textContent = c ? `${fmt(c.big_trees)} big · ${fmt(c.small_trees)} small` : "train the counter";
        $("k-cover").textContent = c ? `${c.tree_cover_pct}%` : `${r.tree_cover_pct_segmentation}%`;
        $("k-cover-seg").textContent = `tree pixels in map: ${r.tree_cover_pct_segmentation}%`;
        $("k-density").textContent = c ? fmt(c.trees_per_ha) : "–";
        $("k-area").textContent = r.area_ha >= 1 ? `${r.area_ha} ha` : `${fmt(Math.round(r.area_m2))} m²`;
        $("k-px").textContent = `${r.width} × ${r.height} px at 10 m`;
        const t = r.ground_truth;
        $("truth").hidden = !t;
        if (t) $("truth").innerHTML = `<b>Hand count for this square:</b> ${fmt(t.total_trees)} trees (${fmt(t.big_trees)} big · ${fmt(t.small_trees)} small), tree cover ${t.tree_cover_pct}%. ` +
            `AI estimate: ${c ? fmt(c.total_trees) : "n/a"} trees, ${c ? c.tree_cover_pct : "–"}% cover. ` +
            `<span class="hint">This square was used to calibrate the counter, so the numbers here are not an independent test.</span>`;
        $("img-rgb").src = r.rgb_png;
        $("img-cls").src = r.class_png;
        const tb = $("cls-table").querySelector("tbody");
        tb.innerHTML = "";
        for (const k of r.classes.filter((x) => x.pixels > 0).sort((a, b) => b.percent - a.percent)) {
            tb.insertAdjacentHTML("beforeend",
                `<tr><td><span class="sw" style="background:${k.color}"></span>${k.label}</td><td>${k.percent}</td>` +
                `<td>${fmt(Math.round(k.area_m2))}</td><td style="width:40%"><div class="bar" style="width:${k.percent}%;background:${k.color}"></div></td></tr>`);
        }
    }

    async function analyse(src) {
        let opts;
        if (src === "file") {
            const f = $("src-file").files[0];
            if (!f) return status("Choose a .tif file first.", "warning");
            const fd = new FormData(); fd.append("file", f);
            opts = { method: "POST", body: fd };
        } else {
            const body = {};
            if (src === "job") { const v = $("src-job").value; if (!v) return status("No collected area selected.", "warning"); const [id, y] = v.split("|"); body.job_id = id; body.year = y; }
            if (src === "gaz") body.gazipur_id = $("src-gaz").value;
            if (src === "lab") body.labelled = $("src-lab").value;
            opts = { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
        }
        status("Running the 10-band model…");
        try {
            const d = await (await fetch("/monitor/analyze", opts)).json();
            if (!d.success) return status(d.message + (d.error ? ` (${d.error})` : ""), "error");
            status("");
            show(d.result);
        } catch (e) { status(`Request failed: ${e}`, "error"); }
    }

    document.querySelectorAll("[data-src]").forEach((b) => b.addEventListener("click", () => analyse(b.dataset.src)));
    loadSources().catch((e) => status(`Could not load sources: ${e}`, "error"));
})();
