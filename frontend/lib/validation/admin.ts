import { z } from "zod";

const money = z.object({ currency: z.string(), amount: z.number() });

export const overviewSchema = z.object({
  registrations: z.number(),
  registrations_30d: z.number(),
  active_candidates: z.number(),
  suspended: z.number(),
  completed_profiles: z.number(),
  published_websites: z.number(),
  enabled_employer_profiles: z.number(),
  payments_total: z.number(),
  payments_successful: z.number(),
  revenue: z.array(money),
  revenue_30d: z.array(money),
  open_support_tickets: z.number(),
  signups_by_day: z.array(z.object({ date: z.string(), count: z.number() })),
});

const page = <T extends z.ZodTypeAny>(item: T) =>
  z.object({ count: z.number(), next: z.string().nullable(), previous: z.string().nullable(), results: z.array(item) });

export const adminUserRowSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  date_joined: z.string(),
  last_login: z.string().nullable(),
  is_active: z.boolean(),
  has_profile: z.boolean(),
  is_pro: z.boolean(),
  website: z.enum(["none", "published", "blocked"]),
  ai_profile: z.enum(["off", "enabled", "admin_disabled"]),
});
export const adminUserPageSchema = page(adminUserRowSchema);

export const adminPaymentSchema = z.object({
  id: z.string(),
  user_id: z.number(),
  user_email: z.string(),
  product: z.string(),
  amount: z.number(),
  currency: z.string(),
  provider: z.string(),
  status: z.string(),
  refunded_amount: z.number(),
  refund_status: z.enum(["none", "partial", "full"]),
  provider_order_id: z.string().nullable(),
  provider_payment_id: z.string(),
  created_at: z.string(),
  paid_at: z.string().nullable(),
});
export const adminPaymentPageSchema = page(adminPaymentSchema);

export const auditEntrySchema = z.object({
  id: z.number(),
  action: z.string(),
  actor_type: z.string(),
  actor_email: z.string().nullable(),
  subject_user_id: z.number().nullable(),
  subject_email: z.string().nullable(),
  target_type: z.string(),
  target_id: z.string(),
  metadata: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});
export const auditPageSchema = page(auditEntrySchema);

export const adminUserDetailSchema = adminUserRowSchema.extend({
  profile: z.record(z.string(), z.unknown()).nullable(),
  entitlements: z.array(
    z.object({
      code: z.string(),
      source: z.string(),
      reason: z.string(),
      granted_at: z.string(),
      revoked_at: z.string().nullable(),
      granted_by: z.string().nullable(),
    }),
  ),
  payments: z.array(adminPaymentSchema),
  website_detail: z.object({
    slug: z.string().nullable(),
    template: z.string().nullable(),
    published_version: z.number().nullable(),
    admin_blocked: z.boolean(),
    admin_blocked_reason: z.string(),
  }),
  ai_profile_detail: z.object({
    enabled: z.boolean(),
    admin_disabled: z.boolean(),
    admin_disabled_reason: z.string(),
    chatbot_enabled: z.boolean(),
    matching_enabled: z.boolean(),
  }),
  support: z.object({ total: z.number(), open: z.number() }),
  audit: z.array(auditEntrySchema),
});

const failure = z.object({
  id: z.number(),
  user_id: z.number().nullable(),
  user_email: z.string().nullable(),
  error_code: z.string(),
  at: z.string().nullable(),
});
export const aiJobsSchema = z.object({
  window_days: z.number(),
  pipelines: z.array(
    z.object({ key: z.string(), label: z.string(), counts: z.record(z.string(), z.number()), failures: z.array(failure), stuck: z.number() }),
  ),
});

export const adminTemplateSchema = z.object({
  key: z.string(),
  name: z.string(),
  description: z.string(),
  enabled: z.boolean(),
  premium: z.boolean(),
  sections: z.array(z.string()),
  supported: z.array(z.string()),
  sites: z.number(),
  published_sites: z.number(),
});
export const templateVersionPageSchema = page(
  z.object({ number: z.number(), note: z.string(), changed_by: z.string().nullable(), created_at: z.string() }),
);

export const USER_ACTIONS = {
  suspend: { label: "Suspend account", danger: true },
  reactivate: { label: "Reactivate account", danger: false },
  disable_ai_profile: { label: "Disable AI profile", danger: true },
  enable_ai_profile: { label: "Re-enable AI profile", danger: false },
  take_site_offline: { label: "Take website offline", danger: true },
  allow_publishing: { label: "Allow publishing", danger: false },
  grant_pro: { label: "Grant Pro", danger: false },
  revoke_pro: { label: "Revoke Pro", danger: true },
} as const;
export type UserAction = keyof typeof USER_ACTIONS;

/** Actions that make sense for a user's current state. */
export function availableActions(u: z.infer<typeof adminUserDetailSchema>): UserAction[] {
  return [
    u.is_active ? "suspend" : "reactivate",
    u.ai_profile_detail.admin_disabled ? "enable_ai_profile" : "disable_ai_profile",
    u.website_detail.admin_blocked ? "allow_publishing" : "take_site_offline",
    u.is_pro ? "revoke_pro" : "grant_pro",
  ];
}

/** "?a=1&b=x" from non-empty values (page omitted when 1). */
export function adminQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    if (k === "page" && Number(v) <= 1) continue;
    q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** Editable section list: the chosen defaults in order, then the template's other supported sections, unticked. */
export function sectionRows(supported: string[], chosen: string[]): { key: string; on: boolean }[] {
  const picked = chosen.filter((k) => supported.includes(k));
  return [...picked.map((key) => ({ key, on: true })), ...supported.filter((k) => !picked.includes(k)).map((key) => ({ key, on: false }))];
}

/** Admin template preview URL for a section order. */
export function templatePreviewHref(key: string, sections: string[]): string {
  return `/template-preview/${encodeURIComponent(key)}?sections=${sections.map(encodeURIComponent).join(",")}`;
}
