import type { z } from "zod";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Django's CSRF token, set as a readable cookie by the backend. */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

type RequestOptions = {
  method?: string;
  /** Plain objects are sent as JSON; FormData is sent as multipart. */
  body?: unknown;
  /** Status codes that are part of the contract rather than failures. */
  okStatuses?: number[];
};

/**
 * Call a same-origin backend URL and validate the JSON body against `schema`.
 * Unexpected statuses throw ApiError carrying the parsed body so callers can
 * render structured errors.
 */
export async function request<T extends z.ZodType>(
  url: string,
  schema: T,
  { method = "GET", body, okStatuses = [] }: RequestOptions = {},
): Promise<z.infer<T>> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let payload: BodyInit | undefined;

  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  if (UNSAFE_METHODS.has(method)) {
    const token = getCsrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }

  const response = await fetch(url, {
    method,
    headers,
    body: payload,
    credentials: "same-origin",
  });
  const data: unknown = await response.json().catch(() => null);

  if (!response.ok && !okStatuses.includes(response.status)) {
    throw new ApiError(`${method} ${url} failed with ${response.status}`, response.status, data);
  }
  return schema.parse(data);
}

/** GET a Django REST endpoint under /api. */
export function apiGet<T extends z.ZodType>(path: string, schema: T): Promise<z.infer<T>> {
  return request(`/api${path}`, schema);
}

/** POST/PUT/PATCH/DELETE a Django REST endpoint under /api. */
export function apiSend<T extends z.ZodType>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  schema: T,
  body?: unknown,
): Promise<z.infer<T>> {
  return request(`/api${path}`, schema, { method, body });
}
