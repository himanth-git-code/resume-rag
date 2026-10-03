import type { z } from "zod";

import type { supportMessageSchema, ticketSchema, ticketSummarySchema } from "@/lib/validation/support";

export type TicketSummary = z.infer<typeof ticketSummarySchema>;
export type Ticket = z.infer<typeof ticketSchema>;
export type SupportMessage = z.infer<typeof supportMessageSchema>;
