import { describe, expect, it } from "vitest";

import {
  flattenServerErrors,
  isSafeLink,
  profileFormSchema,
  profileSchema,
  toFormValues,
  toPayload,
} from "@/lib/validation/profile";

const draft = profileSchema.parse({
  full_name: "Jane Doe",
  headline: null,
  email: "jane@example.com",
  skills: [{ name: "Python", category: null, source_type: "resume" }],
  experience: [
    {
      company: "Acme Corp",
      title: null,
      is_current: true,
      responsibilities: ["Built APIs", "Mentored juniors"],
      achievements: [],
      technologies: ["Django", "Redis"],
      source_type: "resume",
    },
  ],
});

describe("toFormValues / toPayload", () => {
  it("round-trips a draft, keeping missing data missing", () => {
    const form = toFormValues(draft);
    expect(form.headline).toBe("");
    expect(form.experience[0].responsibilities).toBe("Built APIs\nMentored juniors");
    expect(form.experience[0].technologies).toBe("Django, Redis");

    const payload = toPayload(form, 7);
    expect(payload.job_id).toBe(7);
    expect(payload.headline).toBeNull();
    expect(payload.experience[0]).toMatchObject({
      company: "Acme Corp",
      title: null,
      is_current: true,
      responsibilities: ["Built APIs", "Mentored juniors"],
      technologies: ["Django", "Redis"],
      source_type: "resume",
    });
    expect(payload.skills[0].source_type).toBe("resume");
  });

  it("drops blank list entries and treats an unticked 'current' as not stated", () => {
    const form = toFormValues(draft);
    form.experience[0].responsibilities = "One\n\n  \nTwo  ";
    form.experience[0].technologies = "Go, , Rust,";
    form.experience[0].is_current = false;
    const payload = toPayload(form);
    expect(payload.job_id).toBeNull();
    expect(payload.experience[0].responsibilities).toEqual(["One", "Two"]);
    expect(payload.experience[0].technologies).toEqual(["Go", "Rust"]);
    expect(payload.experience[0].is_current).toBeNull();
  });

  it("builds an empty form when there is no profile yet", () => {
    const form = toFormValues(null);
    expect(form.full_name).toBe("");
    expect(form.experience).toEqual([]);
  });
});

describe("profileFormSchema", () => {
  const valid = toFormValues(draft);

  it("accepts a reviewed draft", () => {
    expect(profileFormSchema.safeParse(valid).success).toBe(true);
  });

  it("requires a company or job title for each role", () => {
    const form = toFormValues(draft);
    form.experience[0].company = "";
    const result = profileFormSchema.safeParse(form);
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["experience", 0, "company"]);
  });

  it("rejects unsafe links", () => {
    const form = toFormValues(draft);
    form.links = [{ id: null, source_type: "candidate_input", label: "x", url: "javascript:alert(1)" }];
    expect(profileFormSchema.safeParse(form).success).toBe(false);
  });
});

describe("isSafeLink", () => {
  it.each(["https://x.dev", "http://x.dev", "linkedin.com/in/jane", "localhost:3000/cv", ""])("allows %s", (v) => {
    expect(isSafeLink(v)).toBe(true);
  });
  it.each(["javascript:alert(1)", "data:text/html,hi", "JavaScript:void(0)", "ftp://x"])("rejects %s", (v) => {
    expect(isSafeLink(v)).toBe(false);
  });
});

describe("flattenServerErrors", () => {
  it("maps nested DRF errors to form paths", () => {
    const body = {
      full_name: ["Too long."],
      experience: [{}, { non_field_errors: ["Add at least a company or a job title."] }],
      links: [{ url: ["Enter a web address."] }],
    };
    expect(flattenServerErrors(body)).toEqual([
      { path: "full_name", message: "Too long." },
      { path: "experience.1", message: "Add at least a company or a job title." },
      { path: "links.0.url", message: "Enter a web address." },
    ]);
  });
});

describe("item ids", () => {
  it("round-trips existing ids and leaves new items without one", () => {
    const saved = profileSchema.parse({
      skills: [{ id: 42, name: "Python", category: null, source_type: "resume" }],
      experience: [{ id: 7, company: "Acme", source_type: "candidate_input" }],
    });
    const form = toFormValues(saved);
    expect(form.skills[0].id).toBe(42);
    form.skills.push({ id: null, source_type: "candidate_input", name: "Go", category: "" });

    const payload = toPayload(form);
    expect(payload.skills.map((k) => k.id)).toEqual([42, null]);
    expect(payload.experience[0].id).toBe(7);
  });

  it("treats draft items as new", () => {
    expect(toFormValues(draft).skills[0].id).toBeNull();
  });
});
