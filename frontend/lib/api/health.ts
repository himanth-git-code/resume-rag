import { useQuery } from "@tanstack/react-query";

import { ApiError, apiGet } from "@/lib/api/client";
import { healthSchema } from "@/lib/validation/health";
import type { Health } from "@/types/health";

async function fetchHealth(): Promise<Health> {
  try {
    return await apiGet("/health", healthSchema);
  } catch (error) {
    // A 503 still carries a per-component report worth showing.
    if (error instanceof ApiError && error.status === 503) {
      const report = healthSchema.safeParse(error.body);
      if (report.success) return report.data;
    }
    throw error;
  }
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
  });
}
