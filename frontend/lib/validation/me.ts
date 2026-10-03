import { z } from "zod";

import { parseStatusSchema } from "@/lib/validation/resume";

export const meSchema = z.object({
  id: z.number(),
  email: z.string(),
  dashboard: z.object({
    has_resume: z.boolean(),
    latest_parse_status: parseStatusSchema.nullable(),
    latest_job_id: z.number().nullable(),
    has_profile: z.boolean(),
  }),
  knowledge_base: z.object({
    status: z.enum(["idle", "indexing", "ready", "failed"]),
    chunk_count: z.number(),
    indexed_at: z.string().nullable(),
  }),
  entitlements: z.array(z.string()).default([]),
  is_staff: z.boolean().default(false),
  is_superuser: z.boolean().default(false),
  support_unread: z.number().default(0),
  staff_support_unread: z.number().default(0),
});
