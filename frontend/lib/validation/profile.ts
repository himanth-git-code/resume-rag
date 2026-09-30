import { z } from "zod";

/*
 * Two shapes of the same profile:
 * - API shape (`profileSchema`): missing text is null, lists are arrays. Shared
 *   by GET /api/profile/, the AI draft, and PUT /api/profile/.
 * - Form shape (`profileFormSchema`): every text field is a string ("" = missing);
 *   bullet lists are edited one entry per line, technologies comma-separated.
 * `toFormValues` / `toPayload` convert between them. Validation rules mirror
 * backend/apps/candidates/serializers.py.
 */

const sourceType = z.enum(["resume", "candidate_input"]).catch("candidate_input");
const str = z.string().nullish();
const strList = z.array(z.string()).nullish();

const withSource = <T extends z.ZodRawShape>(shape: T) => z.object({ ...shape, source_type: sourceType.optional() });

export const profileSchema = z.object({
  full_name: str,
  headline: str,
  summary: str,
  email: str,
  phone: str,
  location: str,
  links: z.array(withSource({ label: str, url: z.string() })).default([]),
  skills: z.array(withSource({ name: z.string(), category: str })).default([]),
  experience: z
    .array(
      withSource({
        company: str,
        title: str,
        location: str,
        start_date: str,
        end_date: str,
        is_current: z.boolean().nullish(),
        description: str,
        responsibilities: strList,
        achievements: strList,
        technologies: strList,
      }),
    )
    .default([]),
  education: z
    .array(
      withSource({ institution: str, degree: str, field_of_study: str, start_date: str, end_date: str, grade: str }),
    )
    .default([]),
  certifications: z
    .array(
      withSource({
        name: z.string(),
        issuer: str,
        issue_date: str,
        expiry_date: str,
        credential_id: str,
        url: str,
      }),
    )
    .default([]),
  projects: z
    .array(
      withSource({
        name: z.string(),
        role: str,
        description: str,
        technologies: strList,
        url: str,
        start_date: str,
        end_date: str,
      }),
    )
    .default([]),
  achievements: z.array(withSource({ title: z.string(), description: str, date: str })).default([]),
  updated_at: z.string().optional(),
});

// ---------------------------------------------------------------------------
// Form shape

const text = (max: number) => z.string().trim().max(max, `Keep this under ${max} characters.`);
const required = (max: number, label: string) => text(max).min(1, `${label} is required.`);

/** Same rule as the backend: http(s) or no scheme; never javascript:, data:, … */
export function isSafeLink(value: string): boolean {
  const v = value.trim();
  if (!v) return true;
  const scheme = /^([a-zA-Z][a-zA-Z0-9+.-]*):/.exec(v);
  if (!scheme || /^[\w.-]+:\d/.test(v)) return true;
  return ["http", "https"].includes(scheme[1].toLowerCase());
}

const link = (max: number) =>
  text(max).refine(isSafeLink, "Enter a web address starting with http:// or https://.");

const formSource = z.enum(["resume", "candidate_input"]);
const MAX_ITEMS = 100;
const section = <T extends z.ZodTypeAny>(item: T) => z.array(item).max(MAX_ITEMS, `At most ${MAX_ITEMS} entries.`);

export const profileFormSchema = z.object({
  full_name: text(200),
  headline: text(200),
  summary: text(10000),
  email: text(254),
  phone: text(50),
  location: text(200),
  links: section(z.object({ source_type: formSource, label: text(100), url: link(500).min(1, "URL is required.") })),
  skills: section(z.object({ source_type: formSource, name: required(100, "Skill"), category: text(100) })),
  experience: section(
    z
      .object({
        source_type: formSource,
        company: text(200),
        title: text(200),
        location: text(200),
        start_date: text(50),
        end_date: text(50),
        is_current: z.boolean(),
        description: text(5000),
        responsibilities: z.string(),
        achievements: z.string(),
        technologies: z.string(),
      })
      .refine((e) => e.company || e.title, { message: "Add at least a company or a job title.", path: ["company"] }),
  ),
  education: section(
    z
      .object({
        source_type: formSource,
        institution: text(200),
        degree: text(200),
        field_of_study: text(200),
        start_date: text(50),
        end_date: text(50),
        grade: text(100),
      })
      .refine((e) => e.institution || e.degree, {
        message: "Add at least an institution or a degree.",
        path: ["institution"],
      }),
  ),
  certifications: section(
    z.object({
      source_type: formSource,
      name: required(200, "Name"),
      issuer: text(200),
      issue_date: text(50),
      expiry_date: text(50),
      credential_id: text(200),
      url: link(500),
    }),
  ),
  projects: section(
    z.object({
      source_type: formSource,
      name: required(200, "Name"),
      role: text(200),
      description: text(5000),
      technologies: z.string(),
      url: link(500),
      start_date: text(50),
      end_date: text(50),
    }),
  ),
  achievements: section(
    z.object({ source_type: formSource, title: required(300, "Title"), description: text(5000), date: text(50) }),
  ),
});

// ---------------------------------------------------------------------------
// Conversion

const s = (v: string | null | undefined) => v ?? "";
const lines = (v: string[] | null | undefined) => (v ?? []).join("\n");
const commas = (v: string[] | null | undefined) => (v ?? []).join(", ");
const src = (v: string | undefined) => (v === "resume" ? "resume" : "candidate_input") as "resume" | "candidate_input";

export function toFormValues(profile: z.infer<typeof profileSchema> | null): z.infer<typeof profileFormSchema> {
  const p = profile ?? profileSchema.parse({});
  return {
    full_name: s(p.full_name),
    headline: s(p.headline),
    summary: s(p.summary),
    email: s(p.email),
    phone: s(p.phone),
    location: s(p.location),
    links: p.links.map((l) => ({ source_type: src(l.source_type), label: s(l.label), url: l.url })),
    skills: p.skills.map((k) => ({ source_type: src(k.source_type), name: k.name, category: s(k.category) })),
    experience: p.experience.map((e) => ({
      source_type: src(e.source_type),
      company: s(e.company),
      title: s(e.title),
      location: s(e.location),
      start_date: s(e.start_date),
      end_date: s(e.end_date),
      is_current: e.is_current === true,
      description: s(e.description),
      responsibilities: lines(e.responsibilities),
      achievements: lines(e.achievements),
      technologies: commas(e.technologies),
    })),
    education: p.education.map((e) => ({
      source_type: src(e.source_type),
      institution: s(e.institution),
      degree: s(e.degree),
      field_of_study: s(e.field_of_study),
      start_date: s(e.start_date),
      end_date: s(e.end_date),
      grade: s(e.grade),
    })),
    certifications: p.certifications.map((c) => ({
      source_type: src(c.source_type),
      name: c.name,
      issuer: s(c.issuer),
      issue_date: s(c.issue_date),
      expiry_date: s(c.expiry_date),
      credential_id: s(c.credential_id),
      url: s(c.url),
    })),
    projects: p.projects.map((x) => ({
      source_type: src(x.source_type),
      name: x.name,
      role: s(x.role),
      description: s(x.description),
      technologies: commas(x.technologies),
      url: s(x.url),
      start_date: s(x.start_date),
      end_date: s(x.end_date),
    })),
    achievements: p.achievements.map((a) => ({
      source_type: src(a.source_type),
      title: a.title,
      description: s(a.description),
      date: s(a.date),
    })),
  };
}

const n = (v: string) => (v.trim() ? v.trim() : null);
const splitLines = (v: string) =>
  v
    .split("\n")
    .map((x) => x.trim())
    .filter(Boolean);
const splitCommas = (v: string) =>
  v
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

/** Form values -> PUT /api/profile/ body. Empty text becomes null (missing), not "". */
export function toPayload(form: z.infer<typeof profileFormSchema>, jobId?: number | null) {
  return {
    job_id: jobId ?? null,
    full_name: n(form.full_name),
    headline: n(form.headline),
    summary: n(form.summary),
    email: n(form.email),
    phone: n(form.phone),
    location: n(form.location),
    links: form.links.map((l) => ({ source_type: l.source_type, label: n(l.label), url: l.url.trim() })),
    skills: form.skills.map((k) => ({ source_type: k.source_type, name: k.name.trim(), category: n(k.category) })),
    experience: form.experience.map((e) => ({
      source_type: e.source_type,
      company: n(e.company),
      title: n(e.title),
      location: n(e.location),
      start_date: n(e.start_date),
      end_date: n(e.end_date),
      // Unticked means "not stated", not "not current".
      is_current: e.is_current ? true : null,
      description: n(e.description),
      responsibilities: splitLines(e.responsibilities),
      achievements: splitLines(e.achievements),
      technologies: splitCommas(e.technologies),
    })),
    education: form.education.map((e) => ({
      source_type: e.source_type,
      institution: n(e.institution),
      degree: n(e.degree),
      field_of_study: n(e.field_of_study),
      start_date: n(e.start_date),
      end_date: n(e.end_date),
      grade: n(e.grade),
    })),
    certifications: form.certifications.map((c) => ({
      source_type: c.source_type,
      name: c.name.trim(),
      issuer: n(c.issuer),
      issue_date: n(c.issue_date),
      expiry_date: n(c.expiry_date),
      credential_id: n(c.credential_id),
      url: n(c.url),
    })),
    projects: form.projects.map((x) => ({
      source_type: x.source_type,
      name: x.name.trim(),
      role: n(x.role),
      description: n(x.description),
      technologies: splitCommas(x.technologies),
      url: n(x.url),
      start_date: n(x.start_date),
      end_date: n(x.end_date),
    })),
    achievements: form.achievements.map((a) => ({
      source_type: a.source_type,
      title: a.title.trim(),
      description: n(a.description),
      date: n(a.date),
    })),
  };
}

/**
 * Flatten DRF's nested validation errors into react-hook-form paths, e.g.
 * {experience: [{}, {company: ["…"]}]} -> [{path: "experience.1.company", message: "…"}].
 */
export function flattenServerErrors(body: unknown, prefix = ""): { path: string; message: string }[] {
  if (Array.isArray(body)) {
    if (body.every((x) => typeof x === "string")) {
      return body.length ? [{ path: prefix, message: body[0] as string }] : [];
    }
    return body.flatMap((item, i) => flattenServerErrors(item, prefix ? `${prefix}.${i}` : String(i)));
  }
  if (body && typeof body === "object") {
    return Object.entries(body).flatMap(([key, value]) => {
      // Object-level errors (e.g. "company or title") attach to the item itself.
      const path = key === "non_field_errors" ? prefix : prefix ? `${prefix}.${key}` : key;
      return flattenServerErrors(value, path);
    });
  }
  return [];
}
