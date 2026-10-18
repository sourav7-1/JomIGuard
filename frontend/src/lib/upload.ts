import type { DocumentStatusOut } from "./api";
import { strings } from "./strings";

export const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB
export const MAX_IMAGE_DIMENSION = 3000; // 3000 px

export const ALLOWED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
]);

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validate file type and size.
 */
export function validateFilePrecheck(file: File): ValidationResult {
  const isImage = file.type.startsWith("image/");
  const isPdf = file.type === "application/pdf";

  if (!isImage && !isPdf) {
    return {
      valid: false,
      error: strings.uploadFlow.errFileType,
    };
  }

  // PDFs larger than 10MB cannot be downscaled, reject directly
  if (isPdf && file.size > MAX_FILE_BYTES) {
    return {
      valid: false,
      error: strings.uploadFlow.errFileSize,
    };
  }

  return { valid: true };
}

/**
 * Downscale image if larger than 10 MB or longer than 3000 px.
 * PDFs are never changed.
 */
export async function prepareFileForUpload(file: File): Promise<File> {
  // PDFs are never changed
  if (file.type === "application/pdf" || !file.type.startsWith("image/")) {
    return file;
  }

  return new Promise((resolve) => {
    // If not in a browser environment with canvas, return original
    if (typeof window === "undefined" || typeof document === "undefined") {
      resolve(file);
      return;
    }

    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      const width = img.naturalWidth || img.width;
      const height = img.naturalHeight || img.height;

      const exceedsDimension = width > MAX_IMAGE_DIMENSION || height > MAX_IMAGE_DIMENSION;
      const exceedsSize = file.size > MAX_FILE_BYTES;

      // If within limits, return original file without transcoding
      if (!exceedsDimension && !exceedsSize) {
        resolve(file);
        return;
      }

      // Calculate scale factor
      let targetWidth = width;
      let targetHeight = height;

      if (exceedsDimension) {
        if (width >= height) {
          targetWidth = MAX_IMAGE_DIMENSION;
          targetHeight = Math.round((height * MAX_IMAGE_DIMENSION) / width);
        } else {
          targetHeight = MAX_IMAGE_DIMENSION;
          targetWidth = Math.round((width * MAX_IMAGE_DIMENSION) / height);
        }
      }

      const canvas = document.createElement("canvas");
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d");

      if (!ctx) {
        resolve(file);
        return;
      }

      ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file);
            return;
          }

          const baseName = file.name.replace(/\.[^/.]+$/, "");
          const newName = `${baseName}.jpg`;
          const optimizedFile = new File([blob], newName, {
            type: "image/jpeg",
            lastModified: Date.now(),
          });

          resolve(optimizedFile);
        },
        "image/jpeg",
        0.9
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(file);
    };

    img.src = objectUrl;
  });
}

/**
 * Upload a document with XMLHttpRequest to track upload percentage progress.
 */
export function uploadDocumentWithProgress(
  file: File,
  options: {
    landId?: string;
    docType?: string;
    onProgress?: (percent: number) => void;
  } = {}
): Promise<DocumentStatusOut> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.withCredentials = true;

    if (xhr.upload && options.onProgress) {
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable && evt.total > 0) {
          const percent = Math.min(100, Math.round((evt.loaded / evt.total) * 100));
          options.onProgress?.(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as DocumentStatusOut;
          resolve(data);
        } catch {
          reject(new Error(strings.error.defaultMessage));
        }
      } else {
        if (xhr.status === 401 && window.location.pathname !== "/login") {
          window.dispatchEvent(new Event("jomiguard:unauthorized"));
        }
        let msg: string = strings.uploadFlow.errGenericUpload;
        if (xhr.status === 413) {
          msg = strings.uploadFlow.errFileSize;
        } else if (xhr.status === 415) {
          msg = strings.uploadFlow.errFileType;
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            if (typeof err.detail === "string") {
              msg = err.detail;
            }
          } catch {}
        }
        reject(new Error(msg));
      }
    };

    xhr.onerror = () => {
      window.dispatchEvent(new Event("jomiguard:offline"));
      reject(new Error(strings.error.offlineMessage));
    };

    const formData = new FormData();
    formData.append("file", file);
    if (options.landId) {
      formData.append("land_id", options.landId);
    }
    if (options.docType && options.docType !== "unknown") {
      formData.append("doc_type", options.docType);
    }

    xhr.send(formData);
  });
}
