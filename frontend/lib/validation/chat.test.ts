import { describe, expect, it } from "vitest";

import { chatErrorMessage } from "@/lib/api/chat";
import { ApiError } from "@/lib/api/client";
import { chatTranscriptSchema, sourcesLine } from "@/lib/validation/chat";

describe("sourcesLine", () => {
  it("lists citation labels, or nothing when uncited", () => {
    expect(sourcesLine([])).toBeNull();
    expect(
      sourcesLine([
        { source_type: "experience", source_id: 1, label: "Experience: Engineer at Acme" },
        { source_type: "skills", source_id: null, label: "Skills: Python" },
      ]),
    ).toBe("Sources: Experience: Engineer at Acme · Skills: Python");
  });
});

describe("chatTranscriptSchema", () => {
  it("parses a pending reply", () => {
    const parsed = chatTranscriptSchema.parse({
      session_id: "abc",
      messages: [
        { id: 1, role: "user", content: "Python?", status: "done", answer_status: "", citations: [], created_at: "t" },
        { id: 2, role: "assistant", content: "", status: "pending", answer_status: "", citations: [], created_at: "t" },
      ],
    });
    expect(parsed.messages[1].status).toBe("pending");
  });
});

describe("chatErrorMessage", () => {
  it("uses the server's message and code", () => {
    const err = new ApiError("x", 429, { code: "session_limit", detail: "Start a new one." });
    expect(chatErrorMessage(err)).toEqual({ code: "session_limit", message: "Start a new one." });
  });

  it("falls back for throttling and network errors", () => {
    expect(chatErrorMessage(new ApiError("x", 429, null)).code).toBe("throttled");
    expect(chatErrorMessage(new TypeError("fetch")).code).toBe("network");
  });
});
