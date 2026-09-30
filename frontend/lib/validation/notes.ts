import { z } from "zod";

export const noteSchema = z.object({
  id: z.number(),
  title: z.string(),
  body: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const noteListSchema = z.array(noteSchema);

/** Same limits as the backend (NoteSerializer). */
export const noteInputSchema = z.object({
  title: z.string().trim().min(1, "Add a title.").max(200, "Keep the title under 200 characters."),
  body: z.string().trim().min(1, "Write something.").max(10000, "Keep notes under 10,000 characters."),
});
