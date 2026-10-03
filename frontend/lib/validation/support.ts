import { z } from "zod";

export const TICKET_STATUSES = ["open", "in_progress", "waiting_for_user", "resolved", "closed"] as const;
export const PRIORITIES = ["low", "normal", "high", "urgent"] as const;
export const CANDIDATE_PRIORITIES = ["low", "normal", "high"] as const;

export const STATUS_LABEL: Record<(typeof TICKET_STATUSES)[number], string> = {
  open: "Open",
  in_progress: "In progress",
  waiting_for_user: "Waiting for you",
  resolved: "Resolved",
  closed: "Closed",
};
export const STAFF_STATUS_LABEL = { ...STATUS_LABEL, waiting_for_user: "Waiting for user" };
export const PRIORITY_LABEL: Record<(typeof PRIORITIES)[number], string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

const person = z.object({ id: z.number(), email: z.string(), name: z.string() }).nullable();

export const ticketSummarySchema = z.object({
  number: z.string(),
  subject: z.string(),
  priority: z.enum(PRIORITIES),
  status: z.enum(TICKET_STATUSES),
  unread: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  candidate: person.optional(),
  assigned_to: person.optional(),
});

export const supportMessageSchema = z.object({
  id: z.number(),
  kind: z.enum(["candidate", "staff", "internal", "event"]),
  author: z.object({ name: z.string(), staff: z.boolean() }).nullable(),
  body: z.string(),
  attachments: z.array(
    z.object({ id: z.number(), original_name: z.string(), content_type: z.string(), size: z.number(), url: z.string() }),
  ),
  created_at: z.string(),
});

export const ticketSchema = ticketSummarySchema.extend({
  description: z.string(),
  messages: z.array(supportMessageSchema),
});

export const ticketPageSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(ticketSummarySchema),
});

export const staffListSchema = z.array(z.object({ id: z.number(), email: z.string(), name: z.string() }));

export const MAX_FILES = 3;
const MAX_BYTES = 5 * 1024 * 1024;

/** Client-side pre-check; the server re-validates by content. */
export function checkFiles(files: File[]): string | null {
  if (files.length > MAX_FILES) return `Attach at most ${MAX_FILES} files.`;
  for (const f of files) {
    if (!/\.(png|jpe?g|pdf)$/i.test(f.name)) return `“${f.name}” isn't a PNG, JPEG or PDF.`;
    if (f.size > MAX_BYTES) return `“${f.name}” is larger than 5 MB.`;
  }
  return null;
}

export type StaffFilters = { status?: string; priority?: string; assignee?: string; unread?: boolean; search?: string };

export function staffQuery(filters: StaffFilters, page = 1): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.assignee) params.set("assignee", filters.assignee);
  if (filters.unread) params.set("unread", "1");
  const search = filters.search?.trim();
  if (search) params.set("search", search);
  if (page > 1) params.set("page", String(page));
  const q = params.toString();
  return q ? `?${q}` : "";
}

export function formatBytes(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
