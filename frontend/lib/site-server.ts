import "server-only";

import { headers } from "next/headers";

import { parseSiteData } from "@/lib/validation/site";
import type { SiteData } from "@/types/site";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/**
 * Fetch SiteData from Django on the internal network (server components only).
 * Forwards the visitor's X-Forwarded-For so audit logs and throttles see them.
 * Returns null for 404s (unknown/expired/unpublished).
 */
export async function fetchSiteData(path: string): Promise<SiteData | null> {
  const incoming = await headers();
  const forwarded = incoming.get("x-forwarded-for");
  const response = await fetch(`${BACKEND_URL}${path}`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(forwarded ? { "X-Forwarded-For": forwarded } : {}),
      "User-Agent": incoming.get("user-agent") ?? "",
    },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Site data request failed with ${response.status}`);
  return parseSiteData(await response.json());
}
