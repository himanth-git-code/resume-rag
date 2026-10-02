import type { z } from "zod";

import type { catalogSchema, websiteSchema } from "@/lib/validation/website";

export type WebsiteSettings = z.infer<typeof websiteSchema>;
export type WebsiteCatalog = z.infer<typeof catalogSchema>;
export type WebsiteUpdate = Partial<{
  slug: string | null;
  template: string;
  theme: Partial<WebsiteSettings["theme"]>;
  sections: WebsiteSettings["sections"];
  overrides: Partial<WebsiteSettings["overrides"]>;
  bio_text: string;
  show_chatbot: boolean;
  show_matching: boolean;
}>;
