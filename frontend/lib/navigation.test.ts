import { describe, expect, it } from "vitest";

import { safeNext } from "@/lib/navigation";

describe("safeNext", () => {
  it("keeps same-site relative paths", () => {
    expect(safeNext("/profile?tab=1")).toBe("/profile?tab=1");
  });

  it.each([null, undefined, "", "https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"])(
    "falls back for %s",
    (value) => {
      expect(safeNext(value)).toBe("/dashboard");
    },
  );
});
