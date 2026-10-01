import { describe, expect, it } from "vitest";

import { absoluteUrl, publicProfileSchema } from "@/lib/validation/employer-profile";

describe("absoluteUrl", () => {
  it("keeps http(s) links and adds https to scheme-less ones", () => {
    expect(absoluteUrl("https://x.dev/a")).toBe("https://x.dev/a");
    expect(absoluteUrl("HTTP://x.dev")).toBe("HTTP://x.dev");
    expect(absoluteUrl("github.com/jane")).toBe("https://github.com/jane");
    expect(absoluteUrl("//evil.example")).toBe("https://evil.example");
  });
});

describe("publicProfileSchema", () => {
  it("accepts a profile with hidden sections omitted", () => {
    const parsed = publicProfileSchema.parse({
      profile: { full_name: "Jane", headline: null, experience: [{ company: "Acme", title: null }] },
      chatbot_enabled: true,
      matching_enabled: false,
      turnstile_site_key: null,
    });
    expect(parsed.profile.projects).toBeUndefined();
    expect(parsed.profile.experience?.[0].technologies).toEqual([]);
  });
});
