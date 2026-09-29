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

/**
 * Fetch a same-origin /api path and validate the JSON body against `schema`.
 * Non-2xx responses throw ApiError, but still carry the parsed body so callers
 * can render structured error payloads (e.g. a 503 health report).
 */
export async function apiGet<T extends z.ZodType>(
  path: string,
  schema: T,
  init?: RequestInit,
): Promise<z.infer<T>> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
    credentials: "same-origin",
  });

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(`GET /api${path} failed with ${response.status}`, response.status, body);
  }

  return schema.parse(body);
}
