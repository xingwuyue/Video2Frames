import type { ExportConfig, ExportResult, SessionState } from "./types";

type ApiErrorResponse = {
  error?: unknown;
};

const defaultApiBase = "http://127.0.0.1:8765/api";
const envApiBase = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
  ?.VITE_API_BASE;

let apiBase = normalizeApiBase(envApiBase ?? defaultApiBase);

export function configureApiBase(base: string) {
  apiBase = normalizeApiBase(base);
}

export function getState(): Promise<SessionState> {
  return request<SessionState>("/state");
}

export function importVideo(file: File, sampleEveryNFrames: number): Promise<SessionState> {
  return request<SessionState>("/import", {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      "X-Filename": encodeURIComponent(file.name),
      "X-Sample-Every-N-Frames": String(Math.max(1, Math.floor(sampleEveryNFrames || 1)))
    },
    body: file
  });
}

export function processKey(): Promise<SessionState> {
  return request<SessionState>("/process/key", {
    method: "POST"
  });
}

export function fileUrl(filePath: string): string {
  const encodedPath = filePath
    .split(/[\\/]+/)
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  return `${apiBase}/files/${encodedPath}`;
}

export function exportProject(config?: Partial<ExportConfig>): Promise<ExportResult> {
  return request<ExportResult>("/export", {
    method: "POST",
    headers: config ? { "Content-Type": "application/json" } : undefined,
    body: config ? JSON.stringify(config) : undefined
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  const payload = await parseJson(response);

  if (hasErrorMessage(payload)) {
    throw new Error(payload.error);
  }

  if (!response.ok) {
    throw new Error(errorMessage(response));
  }

  if (payload === undefined) {
    throw new Error("API 响应格式无效。");
  }

  return payload as T;
}

function errorMessage(response: Response): string {
  const fallback = `请求失败，状态码 ${response.status}`;
  return response.statusText ? `${fallback}: ${response.statusText}` : fallback;
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function hasErrorMessage(payload: unknown): payload is { error: string } {
  const error = (payload as ApiErrorResponse | null)?.error;
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof error === "string" &&
    Boolean(error.trim())
  );
}

function normalizeApiBase(base: string): string {
  return base.replace(/\/+$/, "");
}
