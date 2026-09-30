import { z } from "zod";

export const CATEGORIES = ["general", "technical", "experience", "project", "behavioral", "domain"] as const;
export const DIFFICULTIES = ["foundational", "intermediate", "advanced"] as const;

export const categorySchema = z.enum(CATEGORIES);
export const difficultySchema = z.enum(DIFFICULTIES);

const talkingPointSchema = z.object({ ref: z.string(), label: z.string(), text: z.string() });

export const questionSchema = z.object({
  id: z.number(),
  category: categorySchema,
  difficulty: difficultySchema,
  topic: z.string(),
  text: z.string(),
  source_refs: z.array(z.string()),
  talking_points: z.array(talkingPointSchema),
  follow_ups: z.array(
    z.object({ id: z.number(), text: z.string(), difficulty: difficultySchema, talking_points: z.array(talkingPointSchema) }),
  ),
});

export const questionPageSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(questionSchema),
});

export const facetsSchema = z.object({
  total: z.number(),
  categories: z.record(categorySchema, z.number()),
  sources: z.array(z.object({ ref: z.string(), label: z.string(), type: z.string(), count: z.number() })),
});

export const generationSchema = z.object({
  id: z.number(),
  kind: z.enum(["full", "more"]),
  scope: z.object({ category: z.string().optional(), source: z.string().optional() }),
  status: z.enum(["pending", "running", "done", "failed"]),
  sections_total: z.number(),
  sections_done: z.number(),
  error_code: z.string(),
  error_message: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});

export const latestGenerationSchema = z.object({
  generation: generationSchema.nullable(),
  has_profile: z.boolean(),
  profile_changed: z.boolean(),
});

export type QuestionFilters = {
  category?: (typeof CATEGORIES)[number];
  source?: string;
  difficulty?: (typeof DIFFICULTIES)[number];
  search?: string;
};

/** Query string for GET /api/questions/: only set filters, search trimmed. */
export function questionQuery(filters: QuestionFilters, page = 1): string {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.source) params.set("source", filters.source);
  if (filters.difficulty) params.set("difficulty", filters.difficulty);
  const search = filters.search?.trim();
  if (search) params.set("search", search);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** Where a cited profile item can be edited. */
export function refHref(ref: string): string {
  return ref.startsWith("note:") ? "/notes" : "/profile";
}
