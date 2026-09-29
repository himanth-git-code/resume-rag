import { z } from "zod";

export const meSchema = z.object({
  id: z.number(),
  email: z.string(),
  dashboard: z.object({
    has_resume: z.boolean(),
    latest_parse_status: z.string().nullable(),
    has_profile: z.boolean(),
  }),
});
