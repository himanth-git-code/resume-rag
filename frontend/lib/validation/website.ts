import { z } from "zod";

export const websiteSectionSchema = z.object({ key: z.string(), visible: z.boolean() });

export const websiteSchema = z.object({
  slug: z.string().nullable(),
  template: z.string(),
  theme: z.object({ palette: z.string(), mode: z.enum(["light", "dark"]), font: z.string() }),
  sections: z.array(websiteSectionSchema),
  overrides: z.object({
    tagline: z.string().default(""),
    intro: z.string().default(""),
    titles: z.record(z.string(), z.string()).default({}),
    featured_projects: z.array(z.number()).nullable().default(null),
    featured_achievements: z.array(z.number()).nullable().default(null),
    leadership: z.array(z.string()).default([]),
  }),
  bio: z.object({ text: z.string(), source: z.enum(["candidate", "ai"]).nullable(), approved_at: z.string().nullable() }),
  bio_draft: z.object({ status: z.enum(["pending", "done", "failed"]).nullable(), text: z.string().nullable() }),
  show_chatbot: z.boolean(),
  show_matching: z.boolean(),
  updated_at: z.string(),
  has_profile: z.boolean(),
  suggested_slug: z.string().nullable(),
  publish_problems: z.array(z.string()),
  publish: z.object({
    published: z.boolean(),
    version: z.number().nullable(),
    published_at: z.string().nullable(),
    has_changes: z.boolean(),
    path: z.string().nullable(),
  }),
});

export const catalogSchema = z.object({
  templates: z.array(z.object({ key: z.string(), name: z.string(), description: z.string(), sections: z.array(z.string()) })),
  sections: z.record(z.string(), z.string()),
  palettes: z.array(z.object({ key: z.string(), name: z.string() })),
  modes: z.array(z.string()),
  fonts: z.array(z.object({ key: z.string(), name: z.string() })),
});

export const slugAvailabilitySchema = z.object({ available: z.boolean(), detail: z.string().nullable() });

/** Swatch colours for the editor (mirrors components/website-templates/theme.ts). */
export const PALETTE_SWATCH: Record<string, string> = {
  slate: "#334155",
  ocean: "#0b5c8a",
  forest: "#1f6b45",
  plum: "#6b2f7a",
  amber: "#8a4b08",
  rose: "#9f1d45",
};

const SLUG = /^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$/;

/** Client-side mirror of the backend's slug format rule (uniqueness is checked by the API). */
export function slugFormatError(slug: string): string | null {
  return SLUG.test(slug)
    ? null
    : "Use 3–40 lowercase letters, numbers and hyphens, starting and ending with a letter or number.";
}

/** Move an item within a list (for section ordering). */
export function moveItem<T>(items: T[], from: number, to: number): T[] {
  if (to < 0 || to >= items.length) return items;
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
