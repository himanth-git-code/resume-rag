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
});
