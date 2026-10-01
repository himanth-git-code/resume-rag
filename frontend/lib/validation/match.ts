import { z } from "zod";

export const MIN_JD_CHARS = 200;
export const MAX_JD_CHARS = 15_000;

export const matchSchema = z.object({
  id: z.string(),
  source: z.enum(["employer_profile", "candidate_self"]),
  status: z.enum(["pending", "running", "done", "failed"]),
  job_title: z.string(),
  score: z.number().nullable(),
  requirements: z.array(
    z.object({
      text: z.string(),
      importance: z.enum(["required", "preferred"]),
      status: z.enum(["met", "partial", "no_evidence"]),
      evidence: z.array(z.object({ source_type: z.string(), source_id: z.number().nullable(), label: z.string() })),
      explanation: z.string(),
    }),
  ),
  summary: z.object({ strengths: z.array(z.string()).optional(), gaps: z.array(z.string()).optional() }),
  error_message: z.string(),
  disclaimer: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});

export const matchListSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(matchSchema.pick({ id: true, source: true, status: true, job_title: true, score: true, created_at: true })),
});

export const matchErrorSchema = z.object({ code: z.string(), detail: z.string() });

export function checkJobDescription(text: string): string | null {
  const length = text.trim().length;
  if (length < MIN_JD_CHARS) return `Paste the full job description (at least ${MIN_JD_CHARS} characters).`;
  if (length > MAX_JD_CHARS) return `Job descriptions can be at most ${MAX_JD_CHARS.toLocaleString()} characters.`;
  return null;
}

export const isRunning = (status: string | undefined) => status === "pending" || status === "running";
