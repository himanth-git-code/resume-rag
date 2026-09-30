import { z } from "zod";

export const RESUME_MAX_MB = 5;
export const RESUME_ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export const parseStatusSchema = z.enum(["pending", "parsing", "ready_for_review", "applied", "failed"]);

export const resumeJobSchema = z.object({
  id: z.number(),
  status: parseStatusSchema,
  error_code: z.string(),
  error_message: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  document: z.object({
    id: z.number(),
    original_filename: z.string(),
    content_type: z.string(),
    size: z.number(),
  }),
});

export const uploadErrorSchema = z.object({ code: z.string(), detail: z.string() });

/** Client-side pre-check; the server re-validates by file content. */
export function checkResumeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!name.endsWith(".pdf") && !name.endsWith(".docx")) return "Upload a PDF or Word (.docx) file.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > RESUME_MAX_MB * 1024 * 1024) return `Files can be at most ${RESUME_MAX_MB} MB.`;
  return null;
}
