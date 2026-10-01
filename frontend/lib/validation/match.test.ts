import { describe, expect, it } from "vitest";

import { matchErrorMessage } from "@/lib/api/match";
import { ApiError } from "@/lib/api/client";
import { checkJobDescription, isRunning, matchSchema } from "@/lib/validation/match";

describe("checkJobDescription", () => {
  it("enforces the same length limits as the backend", () => {
    expect(checkJobDescription("short")).toMatch(/at least 200/);
    expect(checkJobDescription("x".repeat(15001))).toMatch(/at most/);
    expect(checkJobDescription(` ${"x".repeat(250)} `)).toBeNull();
  });
});

describe("matchSchema", () => {
  it("parses a finished report", () => {
    const parsed = matchSchema.parse({
      id: "abc",
      source: "employer_profile",
      status: "done",
      job_title: "Backend Engineer",
      score: 57,
      requirements: [
        {
          text: "PostgreSQL",
          importance: "required",
          status: "met",
          evidence: [{ source_type: "skills", source_id: null, label: "Skills: PostgreSQL" }],
          explanation: "Lists PostgreSQL.",
        },
      ],
      summary: { strengths: ["PostgreSQL"], gaps: [] },
      error_message: "",
      disclaimer: "This score is an aid…",
      created_at: "t",
      completed_at: "t",
    });
    expect(parsed.requirements[0].status).toBe("met");
  });
});

describe("helpers", () => {
  it("knows when a match is still running", () => {
    expect(isRunning("pending")).toBe(true);
    expect(isRunning("done")).toBe(false);
  });

  it("maps API errors to messages", () => {
    expect(matchErrorMessage(new ApiError("x", 400, { code: "too_short", detail: "Paste more." }))).toBe("Paste more.");
    expect(matchErrorMessage(new ApiError("x", 429, null))).toMatch(/too many/i);
  });
});
