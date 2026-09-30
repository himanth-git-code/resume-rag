import { describe, expect, it } from "vitest";

import { facetsSchema, questionQuery, refHref } from "@/lib/validation/questions";

describe("questionQuery", () => {
  it("includes only set filters and trims search", () => {
    expect(questionQuery({})).toBe("");
    expect(questionQuery({ category: "technical", search: "  redis  " }, 2)).toBe("?category=technical&search=redis&page=2");
    expect(questionQuery({ source: "experience:12", difficulty: "advanced", search: "   " })).toBe(
      "?source=experience%3A12&difficulty=advanced",
    );
  });
});

describe("refHref", () => {
  it("links notes to the notes page and everything else to the profile", () => {
    expect(refHref("note:3")).toBe("/notes");
    expect(refHref("experience:12")).toBe("/profile");
  });
});

describe("facetsSchema", () => {
  it("parses facets from the API", () => {
    const facets = facetsSchema.parse({
      total: 3,
      categories: { general: 1, technical: 2, experience: 0, project: 0, behavioral: 0, domain: 0 },
      sources: [{ ref: "skill:4", label: "Python", type: "skill", count: 2 }],
    });
    expect(facets.categories.technical).toBe(2);
  });
});
