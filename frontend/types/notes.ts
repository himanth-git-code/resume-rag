import type { z } from "zod";

import type { noteInputSchema, noteSchema } from "@/lib/validation/notes";

export type Note = z.infer<typeof noteSchema>;
export type NoteInput = z.infer<typeof noteInputSchema>;
