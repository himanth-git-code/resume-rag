import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import { meSchema } from "@/lib/validation/me";

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet("/me", meSchema),
    enabled,
    // Keep the knowledge base status fresh while it re-indexes in the background.
    refetchInterval: (query) => (query.state.data?.knowledge_base.status === "indexing" ? 3_000 : false),
  });
}
