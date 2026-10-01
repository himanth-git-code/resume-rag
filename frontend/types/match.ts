import type { z } from "zod";

import type { matchSchema } from "@/lib/validation/match";

export type JobMatch = z.infer<typeof matchSchema>;
