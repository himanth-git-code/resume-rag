import { z } from "zod";

export const SECTIONS = [
  "summary",
  "experience",
  "projects",
  "skills",
  "education",
  "certifications",
  "achievements",
  "links",
  "contact",
  "notes",
] as const;
export type Section = (typeof SECTIONS)[number];

export const SECTION_LABEL: Record<Section, { label: string; hint?: string }> = {
  summary: { label: "Summary and location" },
  experience: { label: "Experience" },
  projects: { label: "Projects" },
  skills: { label: "Skills" },
  education: { label: "Education" },
  certifications: { label: "Certifications" },
  achievements: { label: "Achievements" },
  links: { label: "Links" },
  contact: { label: "Contact details", hint: "Your email and phone number." },
  notes: { label: "Notes", hint: "Not shown on the page, but the chatbot may draw on them." },
};

export const employerProfileSchema = z.object({
  enabled: z.boolean(),
  path: z.string(),
  token_created_at: z.string(),
  expires_at: z.string().nullable(),
  visible_sections: z.record(z.enum(SECTIONS), z.boolean()),
  chatbot_enabled: z.boolean(),
  matching_enabled: z.boolean(),
  has_profile: z.boolean().optional(),
});

export const activitySchema = z.object({
  count: z.number(),
  views: z.number(),
  unique_visitors: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(z.object({ id: z.number(), kind: z.enum(["view", "chat_session", "match"]), created_at: z.string() })),
});

const s = z.string().nullish();
const list = z.array(z.string()).default([]);

export const publicProfileSchema = z.object({
  profile: z.object({
    full_name: s,
    headline: s,
    summary: s,
    location: s,
    email: s,
    phone: s,
    experience: z
      .array(
        z.object({
          company: s,
          title: s,
          location: s,
          start_date: s,
          end_date: s,
          is_current: z.boolean().nullish(),
          description: s,
          responsibilities: list,
          achievements: list,
          technologies: list,
        }),
      )
      .optional(),
    projects: z
      .array(z.object({ name: z.string(), role: s, description: s, technologies: list, url: s, start_date: s, end_date: s }))
      .optional(),
    skills: z.array(z.object({ name: z.string(), category: s })).optional(),
    education: z
      .array(z.object({ institution: s, degree: s, field_of_study: s, start_date: s, end_date: s, grade: s }))
      .optional(),
    certifications: z
      .array(z.object({ name: z.string(), issuer: s, issue_date: s, expiry_date: s, credential_id: s, url: s }))
      .optional(),
    achievements: z.array(z.object({ title: z.string(), description: s, date: s })).optional(),
    links: z.array(z.object({ label: s, url: z.string() })).optional(),
  }),
  chatbot_enabled: z.boolean(),
  matching_enabled: z.boolean(),
  turnstile_site_key: z.string().nullable(),
});

/** Turn a scheme-less link ("github.com/jane") into an absolute https URL for an <a href>. */
export function absoluteUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url.replace(/^\/+/, "")}`;
}

/** End of the chosen day in the user's timezone, as ISO (for "expires on" dates). */
export function endOfDayIso(date: string): string {
  return new Date(`${date}T23:59:59`).toISOString();
}
