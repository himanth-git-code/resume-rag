import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import { profileSchema, type toPayload } from "@/lib/validation/profile";
import type { Profile } from "@/types/profile";

async function fetchProfile(): Promise<Profile | null> {
  try {
    return await apiGet("/profile", profileSchema);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function useProfile(enabled = true) {
  return useQuery({ queryKey: ["profile"], queryFn: fetchProfile, enabled });
}

/** The AI draft of a parse job, for review. */
export function useResumeDraft(jobId: number | null) {
  return useQuery({
    queryKey: ["resume-draft", jobId],
    queryFn: () => apiGet(`/resumes/jobs/${jobId}/draft`, profileSchema),
    enabled: jobId !== null,
    staleTime: Infinity,
  });
}

export function useSaveProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReturnType<typeof toPayload>) => apiSend("PUT", "/profile", profileSchema, payload),
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile"], profile);
      queryClient.invalidateQueries({ queryKey: ["resume-job"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
