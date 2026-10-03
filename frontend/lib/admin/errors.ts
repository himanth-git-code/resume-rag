import { ApiError } from "@/lib/api/client";

/** The backend's `detail` message for a failed admin call, or a generic fallback. */
export function errorDetail(error: unknown): string {
  if (error instanceof ApiError && error.body && typeof error.body === "object") {
    const body = error.body as Record<string, unknown>;
    if (typeof body.detail === "string") return body.detail;
    const first = Object.values(body)[0];
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  }
  return "Something went wrong. Please try again.";
}
