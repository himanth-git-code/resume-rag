import { describe, expect, it } from "vitest";

import { period, parseSiteData } from "@/lib/validation/site";
import { moveItem, slugFormatError } from "@/lib/validation/website";

describe("slugFormatError", () => {
  it("accepts valid names and rejects bad formats", () => {
    expect(slugFormatError("jane-doe")).toBeNull();
    expect(slugFormatError("j2")).not.toBeNull();
    expect(slugFormatError("-jane")).not.toBeNull();
    expect(slugFormatError("Jane")).not.toBeNull();
  });
});

describe("moveItem", () => {
  it("moves within bounds and ignores out-of-range moves", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b"], 0, -1)).toEqual(["a", "b"]);
  });
});

describe("site data", () => {
  it("formats periods", () => {
    expect(period("Jan 2020", null, true)).toBe("Jan 2020 – Present");
    expect(period(null, "2019")).toBe("2019");
  });

  it("rejects unexpected shapes", () => {
    expect(parseSiteData({ version: 2 })).toBeNull();
    const ok = {
      version: 1,
      template: "minimal",
      theme: { palette: "slate", mode: "light", font: "inter" },
      hero: { name: "Jane", headline: null, tagline: null, location: null },
      sections: [{ key: "about", title: "About" }],
      content: { about: { intro: null, text: "Hi" } },
      widgets: { chatbot: false, matching: false },
      meta: { title: "Jane", description: "" },
    };
    expect(parseSiteData(ok)?.template).toBe("minimal");
  });
});
