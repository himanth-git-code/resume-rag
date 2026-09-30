import type { z } from "zod";

import type { profileFormSchema, profileSchema } from "@/lib/validation/profile";

export type Profile = z.infer<typeof profileSchema>;
export type ProfileFormValues = z.infer<typeof profileFormSchema>;
export type ProfileSection = "links" | "skills" | "experience" | "education" | "certifications" | "projects" | "achievements";
