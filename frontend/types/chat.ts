import type { z } from "zod";

import type { chatMessageSchema, chatSessionSummarySchema } from "@/lib/validation/chat";

export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type ChatSessionSummary = z.infer<typeof chatSessionSummarySchema>;
