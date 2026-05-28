const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Backend bearer token — only set in production. Frontend reads from a public
// env so the value ships to the browser bundle. This is acceptable for our
// single-tenant setup (the basic-auth gate in middleware.ts is what actually
// keeps strangers out); the token still rate-limits casual API probing and
// is rotated by changing the env in both Vercel and Coolify.
const API_BEARER_TOKEN = process.env.NEXT_PUBLIC_API_BEARER_TOKEN ?? "";

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

function authHeaders(): Record<string, string> {
  return API_BEARER_TOKEN ? { Authorization: `Bearer ${API_BEARER_TOKEN}` } : {};
}

function jsonHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...authHeaders(),
    ...extra,
  };
}

/** Headers for non-JSON paths (e.g. multipart upload). */
export function apiAuthHeaders(): Record<string, string> {
  return { Accept: "application/json", ...authHeaders() };
}

/** Build a useful error message from a failed Response, capping body length. */
async function _readErr(res: Response, method: string, path: string): Promise<string> {
  try {
    const txt = (await res.text()).slice(0, 400);
    return txt
      ? `${method} ${path} failed: ${res.status} — ${txt}`
      : `${method} ${path} failed: ${res.status}`;
  } catch {
    return `${method} ${path} failed: ${res.status}`;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path), { headers: apiAuthHeaders() });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "GET", path));
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "POST", path));
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "PUT",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "PUT", path));
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "PATCH",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "PATCH", path));
  return res.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(apiUrl(path), {
    method: "DELETE",
    headers: apiAuthHeaders(),
  });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "DELETE", path));
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) throw new ApiError(res.status, await _readErr(res, "POST", path));
  return res.json() as Promise<T>;
}
