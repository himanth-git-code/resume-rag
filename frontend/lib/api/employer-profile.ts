import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import { activitySchema, employerProfileSchema, publicProfileSchema } from "@/lib/validation/employer-profile";
import type { EmployerProfileSettings } from "@/types/employer-profile";

const KEY = ["employer-profile"] as const;

export function useEmployerProfile() {
  return useQuery({ queryKey: KEY, queryFn: () => apiGet("/employer-profile", employerProfileSchema) });
}

export function useUpdateEmployerProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: Partial<Omit<EmployerProfileSettings, "path" | "token_created_at" | "has_profile">>) =>
      apiSend("PUT", "/employer-profile", employerProfileSchema, changes),
    onSuccess: (data) => queryClient.setQueryData(KEY, (old: EmployerProfileSettings | undefined) => ({ ...old, ...data })),
  });
}

export function useRegenerateLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiSend("POST", "/employer-profile/regenerate-link", employerProfileSchema),
    onSuccess: (data) => queryClient.setQueryData(KEY, (old: EmployerProfileSettings | undefined) => ({ ...old, ...data })),
  });
}

export function useProfileActivity(page = 1) {
  return useQuery({
    queryKey: [...KEY, "activity", page],
    queryFn: () => apiGet(`/employer-profile/activity${page > 1 ? `?page=${page}` : ""}`, activitySchema),
  });
}

/** Public employer view by secret token. null = link not available (unknown, disabled or expired). */
export function usePublicProfile(token: string) {
  return useQuery({
    queryKey: ["public-profile", token],
    queryFn: async () => {
      try {
        return await apiGet(`/public/p/${encodeURIComponent(token)}`, publicProfileSchema);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
    staleTime: 5 * 60_000,
  });
}
