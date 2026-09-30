import { describe, expect, it } from "vitest";

import { noteInputSchema } from "@/lib/validation/notes";

describe("noteInputSchema", () => {
  it("trims and accepts a note", () => {
    expect(noteInputSchema.parse({ title: "  Leadership ", body: " Led a team. " })).toEqual({
      title: "Leadership",
      body: "Led a team.",
    });
  });

  it("requires a title and body within limits", () => {
    expect(noteInputSchema.safeParse({ title: " ", body: "x" }).success).toBe(false);
    expect(noteInputSchema.safeParse({ title: "x", body: "" }).success).toBe(false);
    expect(noteInputSchema.safeParse({ title: "x", body: "y".repeat(10001) }).success).toBe(false);
  });
});
