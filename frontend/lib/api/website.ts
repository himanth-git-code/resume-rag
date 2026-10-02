import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiGet, apiSend } from "@/lib/api/client";
import { catalogSchema, slugAvailabilitySchema, websiteSchema } from "@/lib/validation/website";
import type { WebsiteUpdate } from "@/types/website";

const KEY = ["website"] as const;

export function useWebsite() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => apiGet("/website", websiteSchema),
    // Keep polling while an AI bio draft is being written.
    refetchInterval: (q) => (q.state.data?.bio_draft.status === "pending" ? 2_000 : false),
  });
}

export function useWebsiteCatalog() {
  return useQuery({ queryKey: ["website-catalog"], queryFn: () => apiGet("/website/catalog", catalogSchema), staleTime: Infinity });
}

export function useUpdateWebsite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: WebsiteUpdate) => apiSend("PUT", "/website", websiteSchema, changes),
    onSuccess: (data) => queryClient.setQueryData(KEY, data),
  });
}

export function useDraftBio() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (person: "first" | "third") => apiSend("POST", "/website/bio/draft", websiteSchema, { person }),
    onSuccess: (data) => queryClient.setQueryData(KEY, data),
  });
}

export function useOpenPreview() {
  return useMutation({
    mutationFn: () => apiSend("POST", "/website/preview", z.object({ path: z.string(), expires_at: z.string() })),
  });
}

export async function checkSlug(slug: string) {
  return apiGet(`/website/slug-available?slug=${encodeURIComponent(slug)}`, slugAvailabilitySchema);
}
