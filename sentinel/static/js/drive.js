/* "Save to Google Drive": the browser signs in to the user's own Google
   account (Google Identity Services popup) and uploads the dataset files
   straight into the Drive folder whose link the user pasted. The server
   never sees or stores the Google token -- it only serves the files.

   Layout in Drive: <pasted folder>/<Area>_2025_Dataset/... -- the same
   folders as the ZIP. Saving again (e.g. after labeling) reuses that folder
   and REPLACES files with the same name instead of creating duplicates. */

(function () {
    "use strict";

    const SCOPE = "https://www.googleapis.com/auth/drive";
    const API = "https://www.googleapis.com/drive/v3";
    const UPLOAD = "https://www.googleapis.com/upload/drive/v3";
    const FOLDER_MIME = "application/vnd.google-apps.folder";
    const LINK_STORAGE_KEY = "driveFolderLink";

    let clientId = "";
    let tokenClient = null;
    let accessToken = null;
    let tokenExpiresAt = 0;
    let gisLoading = null;

    function parseFolderId(link) {
        const text = (link || "").trim();
        if (!text) return null;
        const patterns = [/\/folders\/([A-Za-z0-9_-]{10,})/, /[?&]id=([A-Za-z0-9_-]{10,})/, /^([A-Za-z0-9_-]{20,})$/];
        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    function loadGis() {
        if (window.google && window.google.accounts && window.google.accounts.oauth2) return Promise.resolve();
        if (gisLoading) return gisLoading;
        gisLoading = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://accounts.google.com/gsi/client";
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Could not load Google sign-in. Check your internet connection."));
            document.head.appendChild(script);
        });
        return gisLoading;
    }

    function signedIn() {
        return Boolean(accessToken) && Date.now() < tokenExpiresAt - 60000;
    }

    /* Must be called from a click handler (the sign-in popup needs a user gesture). */
    async function signIn() {
        if (!clientId) throw new Error("Google Drive saving is not set up on this server (GOOGLE_OAUTH_CLIENT_ID is missing).");
        if (signedIn()) return accessToken;
        await loadGis();
        return new Promise((resolve, reject) => {
            tokenClient = window.google.accounts.oauth2.initTokenClient({
                client_id: clientId,
                scope: SCOPE,
                callback: (response) => {
                    if (response.error) {
                        reject(new Error(response.error_description || response.error));
                        return;
                    }
                    accessToken = response.access_token;
                    tokenExpiresAt = Date.now() + Number(response.expires_in || 3600) * 1000;
                    resolve(accessToken);
                },
                error_callback: (error) => reject(new Error(error && error.message ? error.message : "Google sign-in was cancelled."))
            });
            tokenClient.requestAccessToken({ prompt: accessToken ? "" : "consent" });
        });
    }

    async function api(path, options = {}) {
        const response = await fetch(path.startsWith("http") ? path : `${API}${path}`, {
            ...options,
            headers: { Authorization: `Bearer ${accessToken}`, ...(options.headers || {}) }
        });
        if (!response.ok) {
            let message = `Google Drive error ${response.status}`;
            try {
                const body = await response.json();
                message = (body.error && body.error.message) || message;
            } catch (e) { /* not JSON */ }
            if (response.status === 401) accessToken = null;
            throw new Error(message);
        }
        return response;
    }

    function escapeQuery(text) {
        return text.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    }

    async function findChild(parentId, name, folderOnly) {
        const q = `'${parentId}' in parents and name = '${escapeQuery(name)}' and trashed = false` + (folderOnly ? ` and mimeType = '${FOLDER_MIME}'` : "");
        const response = await api(`/files?q=${encodeURIComponent(q)}&fields=files(id,name,mimeType)&pageSize=10&supportsAllDrives=true&includeItemsFromAllDrives=true`);
        const data = await response.json();
        return data.files && data.files.length ? data.files[0] : null;
    }

    async function ensureFolder(parentId, name) {
        const existing = await findChild(parentId, name, true);
        if (existing) return existing.id;
        const response = await api("/files?supportsAllDrives=true&fields=id", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, mimeType: FOLDER_MIME, parents: [parentId] })
        });
        return (await response.json()).id;
    }

    async function checkFolder(folderId) {
        const response = await api(`/files/${folderId}?fields=id,name,mimeType,capabilities(canAddChildren)&supportsAllDrives=true`);
        const info = await response.json();
        if (info.mimeType !== FOLDER_MIME) throw new Error("That link is not a Google Drive folder.");
        if (info.capabilities && info.capabilities.canAddChildren === false) {
            throw new Error(`You don't have permission to add files to "${info.name}".`);
        }
        return info;
    }

    /* Resumable upload: create or replace one file. */
    async function uploadFile(parentId, name, blob, onProgress) {
        const existing = await findChild(parentId, name, false);
        const mime = blob.type || "application/octet-stream";
        const start = await api(
            existing
                ? `${UPLOAD}/files/${existing.id}?uploadType=resumable&supportsAllDrives=true`
                : `${UPLOAD}/files?uploadType=resumable&supportsAllDrives=true`,
            {
                method: existing ? "PATCH" : "POST",
                headers: { "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime },
                body: JSON.stringify(existing ? { name } : { name, parents: [parentId] })
            }
        );
        const sessionUrl = start.headers.get("Location");
        if (!sessionUrl) throw new Error("Google Drive did not return an upload session.");
        await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("PUT", sessionUrl);
            xhr.setRequestHeader("Content-Type", mime);
            xhr.upload.onprogress = (event) => { if (event.lengthComputable && onProgress) onProgress(event.loaded); };
            xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload of ${name} failed (${xhr.status}).`)));
            xhr.onerror = () => reject(new Error(`Network error while uploading ${name}.`));
            xhr.send(blob);
        });
        return existing ? "replaced" : "created";
    }

    /* Upload the whole dataset of one job into the pasted folder. */
    async function saveJob(jobId, folderLink, onStatus) {
        const folderId = parseFolderId(folderLink);
        if (!folderId) throw new Error("Paste a Google Drive folder link (https://drive.google.com/drive/folders/...).");
        await signIn();
        const folder = await checkFolder(folderId);

        const manifest = await (await fetch(`/historical/dataset-manifest/${jobId}`)).json();
        if (!manifest.success) throw new Error(manifest.message || "Nothing to save yet.");

        const totalBytes = manifest.files.reduce((sum, file) => sum + file.size, 0);
        let doneBytes = 0;
        const folderCache = new Map([["", folderId]]);
        async function folderFor(parts) {
            let key = "";
            let parent = folderId;
            for (const part of parts) {
                key = key ? `${key}/${part}` : part;
                if (!folderCache.has(key)) folderCache.set(key, await ensureFolder(parent, part));
                parent = folderCache.get(key);
            }
            return parent;
        }

        const counts = { created: 0, replaced: 0 };
        for (const [index, file] of manifest.files.entries()) {
            const parts = file.path.split("/");
            const name = parts.pop();
            const parentId = await folderFor(parts);
            onStatus(`Uploading ${index + 1}/${manifest.files.length}: ${name}`, doneBytes / totalBytes);
            const response = await fetch(`/historical/dataset-file/${jobId}?path=${encodeURIComponent(file.path)}`);
            if (!response.ok) throw new Error(`Could not read ${file.path} from the server.`);
            const blob = await response.blob();
            const result = await uploadFile(parentId, name, blob, (loaded) => {
                onStatus(`Uploading ${index + 1}/${manifest.files.length}: ${name}`, (doneBytes + loaded) / totalBytes);
            });
            counts[result] += 1;
            doneBytes += file.size;
        }
        fetch(`/historical/mark-exported/${jobId}`, { method: "POST" }).catch(() => {});
        const datasetFolderId = folderCache.get(manifest.root);
        return {
            folderName: folder.name,
            datasetFolder: manifest.root,
            url: `https://drive.google.com/drive/folders/${datasetFolderId || folderId}`,
            fileCount: manifest.files.length,
            counts,
            totalBytes
        };
    }

    /* Wires one "Save to Drive" panel: link input, button, status line. */
    function attachPanel({ input, button, status, getJobId }) {
        try { input.value = localStorage.getItem(LINK_STORAGE_KEY) || ""; } catch (e) { /* storage blocked */ }
        input.addEventListener("change", () => {
            try { localStorage.setItem(LINK_STORAGE_KEY, input.value.trim()); } catch (e) { /* storage blocked */ }
        });

        const setStatus = (html, kind) => {
            status.innerHTML = html;
            status.className = "drive-status" + (kind ? ` ${kind}` : "");
            status.hidden = !html;
        };

        if (!clientId) {
            button.disabled = true;
            setStatus("Google Drive saving is not set up on this server yet (see README: GOOGLE_OAUTH_CLIENT_ID).", "warn");
        }

        let busy = false;
        button.addEventListener("click", async () => {
            const jobId = getJobId();
            if (busy || !jobId) return;
            if (!parseFolderId(input.value)) {
                setStatus("Paste a Google Drive folder link first.", "error");
                input.focus();
                return;
            }
            try { localStorage.setItem(LINK_STORAGE_KEY, input.value.trim()); } catch (e) { /* storage blocked */ }
            busy = true;
            button.disabled = true;
            const original = button.textContent;
            button.textContent = signedIn() ? "Saving…" : "Signing in…";
            try {
                const result = await saveJob(jobId, input.value, (text, fraction) => {
                    button.textContent = "Saving…";
                    setStatus(`${text} <span class="drive-pct">${Math.round(Math.min(1, fraction || 0) * 100)}%</span>`);
                });
                setStatus(
                    `Saved ${result.fileCount} files (${(result.totalBytes / 1048576).toFixed(1)} MB) to ` +
                    `<a href="${result.url}" target="_blank" rel="noopener">${result.folderName} / ${result.datasetFolder}</a>` +
                    (result.counts.replaced ? ` -- ${result.counts.replaced} replaced, ${result.counts.created} new.` : "."),
                    "ok"
                );
            } catch (error) {
                setStatus(String(error.message || error), "error");
            } finally {
                busy = false;
                button.disabled = false;
                button.textContent = original;
            }
        });
    }

    window.DriveSave = {
        configure(id) { clientId = id || ""; },
        attachPanel,
        parseFolderId
    };
})();
