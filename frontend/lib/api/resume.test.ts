import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { isInProgress, uploadErrorMessage } from "@/lib/api/resume";

describe("uploadErrorMessage", () => {
  it("shows the server's message for rejected files", () => {
    const body = { code: "no_text", detail: "We couldn't read any text in this PDF." };
    expect(uploadErrorMessage(new ApiError("bad", 400, body))).toBe(body.detail);
  });

  it("explains throttling", () => {
    expect(uploadErrorMessage(new ApiError("slow down", 429, { detail: "x" }))).toMatch(/wait/);
  });

  it("falls back to a generic message", () => {
    expect(uploadErrorMessage(new TypeError("Failed to fetch"))).toMatch(/upload failed/i);
  });
});

describe("isInProgress", () => {
  it("is true only while queued or parsing", () => {
    expect(isInProgress("pending")).toBe(true);
    expect(isInProgress("parsing")).toBe(true);
    expect(isInProgress("ready_for_review")).toBe(false);
    expect(isInProgress("failed")).toBe(false);
  });
});
