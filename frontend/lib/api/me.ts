import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import { meSchema } from "@/lib/validation/me";

export function useMe(enabled = true) {
  return useQuery({ queryKey: ["me"], queryFn: () => apiGet("/me", meSchema), enabled });
}
