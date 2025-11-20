export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function apiRequest(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

export async function apiUpload<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Upload failed (${res.status})`);
  }
  return res.json();
}

export const loadSampleData = () => apiPost<{ counts: Record<string, number> }>(
  "/data/sample"
);

export const resetDatabase = () => apiPost("/data/reset");

export const uploadCsv = (dataset: "invoices" | "bank_tx", file: File) => {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<{ rows: number }>(`/data/upload/${dataset}`, form);
};

export const scanInvoices = (files: File[]) => {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  return apiUpload<{ rows_appended: number }>("/ocr/scan", form);
};

export const runReconciliation = (payload: {
  date_window_days: number;
  amount_tolerance: number;
  psp_fee_abs: number;
  psp_fee_pct: number;
  only_psp_names: boolean;
  persist: boolean;
}) => apiPost("/reconcile", payload);

export const fetchOverview = (entity = "ALL") =>
  apiGet(`/reporting/overview?entity=${encodeURIComponent(entity)}`);

export const fetchExceptions = () => apiGet("/reporting/exceptions");

export const fetchJournal = () => apiGet("/reporting/journal");

export const BOARD_PACK_URL = `${API_URL}/reports/board-pack`;

