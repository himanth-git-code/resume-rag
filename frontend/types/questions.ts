import type { z } from "zod";

import type { facetsSchema, generationSchema, questionSchema } from "@/lib/validation/questions";

export type Question = z.infer<typeof questionSchema>;
export type QuestionFacets = z.infer<typeof facetsSchema>;
export type QuestionGeneration = z.infer<typeof generationSchema>;
