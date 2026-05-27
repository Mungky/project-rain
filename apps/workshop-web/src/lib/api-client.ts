const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function jsonHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...extra,
  };
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "PUT",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `PUT ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "PATCH",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `PATCH ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(apiUrl(path), {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new ApiError(res.status, `DELETE ${path} failed: ${res.status}`);
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}