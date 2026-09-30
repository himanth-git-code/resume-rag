import { describe, expect, it } from "vitest";

import { checkResumeFile, resumeJobSchema } from "@/lib/validation/resume";

const file = (name: string, bytes: number) => new File([new Uint8Array(bytes)], name);

describe("checkResumeFile", () => {
  it("accepts PDF and DOCX within the size limit", () => {
    expect(checkResumeFile(file("CV.PDF", 1000))).toBeNull();
    expect(checkResumeFile(file("resume.docx", 1000))).toBeNull();
  });

  it("rejects other types, empty and oversized files", () => {
    expect(checkResumeFile(file("resume.doc", 1000))).toMatch(/PDF or Word/);
    expect(checkResumeFile(file("resume.pdf", 0))).toMatch(/empty/);
    expect(checkResumeFile(file("resume.pdf", 5 * 1024 * 1024 + 1))).toMatch(/5 MB/);
  });
});

describe("resumeJobSchema", () => {
  it("parses a job from the API", () => {
    const job = {
      id: 1,
      status: "ready_for_review",
      error_code: "",
      error_message: "",
      created_at: "2026-09-29T10:00:00Z",
      completed_at: null,
      document: { id: 2, original_filename: "cv.pdf", content_type: "application/pdf", size: 1234 },
    };
    expect(resumeJobSchema.parse(job).status).toBe("ready_for_review");
    expect(resumeJobSchema.safeParse({ ...job, status: "done" }).success).toBe(false);
  });
});
