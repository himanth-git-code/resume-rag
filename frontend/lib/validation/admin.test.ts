import { describe, expect, it } from "vitest";

import { sampleSiteData } from "@/lib/admin/sample-site";
import { siteDataSchema } from "@/lib/validation/site";

import {
  adminQuery,
  adminUserDetailSchema,
  adminUserPageSchema,
  auditPageSchema,
  availableActions,
  overviewSchema,
  sectionRows,
  templatePreviewHref,
} from "./admin";

const row = {
  id: 7,
  email: "jane@example.com",
  name: "Jane",
  date_joined: "2026-01-01T00:00:00Z",
  last_login: null,
  is_active: true,
  has_profile: true,
  is_pro: false,
  website: "none",
  ai_profile: "enabled",
};

const detail = {
  ...row,
  profile: null,
  entitlements: [],
  payments: [],
  website_detail: { slug: null, template: null, published_version: null, admin_blocked: false, admin_blocked_reason: "" },
  ai_profile_detail: { enabled: true, admin_disabled: false, admin_disabled_reason: "", chatbot_enabled: true, matching_enabled: true },
  support: { total: 0, open: 0 },
  audit: [],
};

describe("adminQuery", () => {
  it("drops empty values and page 1", () => {
    expect(adminQuery({ search: "", status: "failed", page: 1, unread: false, x: undefined })).toBe("?status=failed");
  });
  it("encodes values and keeps later pages", () => {
    expect(adminQuery({ search: "a b&c", page: 3 })).toBe("?search=a+b%26c&page=3");
  });
  it("returns an empty string when nothing is set", () => {
    expect(adminQuery({})).toBe("");
  });
});

describe("schemas", () => {
  it("parses the overview", () => {
    const parsed = overviewSchema.parse({
      registrations: 3, registrations_30d: 1, active_candidates: 2, suspended: 0, completed_profiles: 2,
      published_websites: 1, enabled_employer_profiles: 1, payments_total: 2, payments_successful: 1,
      revenue: [{ currency: "INR", amount: 99900 }], revenue_30d: [], open_support_tickets: 4,
      signups_by_day: [{ date: "2026-10-01", count: 1 }],
    });
    expect(parsed.revenue[0].amount).toBe(99900);
  });
  it("parses a user page and rejects unknown website states", () => {
    expect(adminUserPageSchema.parse({ count: 1, next: null, previous: null, results: [row] }).results[0].email).toBe("jane@example.com");
    expect(adminUserPageSchema.safeParse({ count: 1, next: null, previous: null, results: [{ ...row, website: "weird" }] }).success).toBe(false);
  });
  it("parses audit entries with metadata", () => {
    const page = auditPageSchema.parse({
      count: 1, next: null, previous: null,
      results: [{
        id: 1, action: "admin.suspend", actor_type: "admin", actor_email: "root@example.com", subject_user_id: 7,
        subject_email: "jane@example.com", target_type: "user", target_id: "7", metadata: { reason: "spam" },
        created_at: "2026-10-01T00:00:00Z",
      }],
    });
    expect(page.results[0].metadata.reason).toBe("spam");
  });
});

describe("availableActions", () => {
  it("offers the opposite of each current state", () => {
    expect(availableActions(adminUserDetailSchema.parse(detail))).toEqual(["suspend", "disable_ai_profile", "take_site_offline", "grant_pro"]);
    const flipped = adminUserDetailSchema.parse({
      ...detail,
      is_active: false,
      is_pro: true,
      website_detail: { ...detail.website_detail, admin_blocked: true },
      ai_profile_detail: { ...detail.ai_profile_detail, admin_disabled: true },
    });
    expect(availableActions(flipped)).toEqual(["reactivate", "enable_ai_profile", "allow_publishing", "revoke_pro"]);
  });
});

describe("template helpers", () => {
  it("lists chosen sections first, then the rest unticked, ignoring unsupported ones", () => {
    expect(sectionRows(["about", "skills", "contact"], ["contact", "about", "bogus"])).toEqual([
      { key: "contact", on: true },
      { key: "about", on: true },
      { key: "skills", on: false },
    ]);
  });
  it("builds the preview URL", () => {
    expect(templatePreviewHref("modern", ["about", "skills"])).toBe("/template-preview/modern?sections=about,skills");
  });
  it("builds valid sample SiteData in the given order, dropping unknown sections", () => {
    const site = sampleSiteData("technical", ["projects", "nope", "about"]);
    expect(siteDataSchema.safeParse(site).success).toBe(true);
    expect(site.sections.map((s) => s.key)).toEqual(["projects", "about"]);
    expect(Object.keys(site.content)).toEqual(["projects", "about"]);
  });
});
