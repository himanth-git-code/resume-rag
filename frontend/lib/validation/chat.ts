import { z } from "zod";

export const chatMessageSchema = z.object({
  id: z.number(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  status: z.enum(["pending", "done", "failed"]),
  answer_status: z.enum(["answered", "not_found", "declined", ""]),
  citations: z.array(z.object({ source_type: z.string(), source_id: z.number().nullable(), label: z.string() })),
  created_at: z.string(),
});

export const chatTranscriptSchema = z.object({
  session_id: z.string(),
  messages: z.array(chatMessageSchema),
});

export const chatErrorSchema = z.object({ code: z.string(), detail: z.string() });

export const chatSessionSummarySchema = z.object({
  id: z.string(),
  question_count: z.number(),
  first_question: z.string(),
  created_at: z.string(),
  last_activity: z.string(),
});

export const chatSessionListSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(chatSessionSummarySchema),
});

export const chatSessionDetailSchema = chatSessionSummarySchema.extend({ messages: z.array(chatMessageSchema) });

export const MAX_QUESTION_CHARS = 1000;

/** "Sources: Experience: Senior Engineer at Acme · Skills: Python" */
export function sourcesLine(citations: z.infer<typeof chatMessageSchema>["citations"]): string | null {
  if (citations.length === 0) return null;
  return `Sources: ${citations.map((c) => c.label).join(" · ")}`;
}
