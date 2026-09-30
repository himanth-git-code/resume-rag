import type { z } from "zod";

import type { parseStatusSchema, resumeJobSchema } from "@/lib/validation/resume";

export type ParseStatus = z.infer<typeof parseStatusSchema>;
export type ResumeJob = z.infer<typeof resumeJobSchema>;
