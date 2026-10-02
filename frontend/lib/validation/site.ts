import { z } from "zod";

import type { SiteData } from "@/types/site";

export const TEMPLATE_KEYS = ["executive", "modern", "technical", "creative", "minimal"] as const;

/** Shallow structural check of SiteData before rendering (the backend owns the detailed shape). */
export const siteDataSchema = z.object({
  version: z.literal(1),
  template: z.enum(TEMPLATE_KEYS),
  theme: z.object({ palette: z.string(), mode: z.enum(["light", "dark"]), font: z.string() }),
  hero: z.object({ name: z.string(), headline: z.string().nullish(), tagline: z.string().nullish(), location: z.string().nullish() }),
  sections: z.array(z.object({ key: z.string(), title: z.string() })),
  content: z.record(z.string(), z.unknown()),
  widgets: z.object({
    chatbot: z.boolean(),
    matching: z.boolean(),
    slug: z.string().optional(),
    turnstile_site_key: z.string().nullish(),
  }),
  meta: z.object({ title: z.string(), description: z.string() }),
});

export function parseSiteData(data: unknown): SiteData | null {
  const parsed = siteDataSchema.safeParse(data);
  return parsed.success ? (data as SiteData) : null;
}

/** "Jan 2020 – Present" from optional parts. */
export function period(start?: string | null, end?: string | null, current?: boolean | null): string {
  return [start, end || (current ? "Present" : null)].filter(Boolean).join(" – ");
}
