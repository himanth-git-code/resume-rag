import type { z } from "zod";

import type { activitySchema, employerProfileSchema, publicProfileSchema } from "@/lib/validation/employer-profile";

export type EmployerProfileSettings = z.infer<typeof employerProfileSchema>;
export type ProfileActivity = z.infer<typeof activitySchema>;
export type PublicProfile = z.infer<typeof publicProfileSchema>;
