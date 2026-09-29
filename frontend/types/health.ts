import type { z } from "zod";

import type { healthSchema } from "@/lib/validation/health";

export type Health = z.infer<typeof healthSchema>;
