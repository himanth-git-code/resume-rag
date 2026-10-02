import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import { isRunning, matchErrorSchema, matchListSchema, matchSchema } from "@/lib/validation/match";

const poll = (q: { state: { data?: { status: string } } }) => (isRunning(q.state.data?.status) ? 2_000 : false);

export function matchErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const parsed = matchErrorSchema.safeParse(error.body);
    if (parsed.success) return parsed.data.detail;
    if (error.status === 429) return "Too many job matches for now. Please try again later.";
    if (error.status === 404) return "Job matching isn't available on this profile.";
  }
  return "The job description couldn't be submitted. Please try again.";
}

/** Public matching (employer profile `/public/p/<token>` or website `/public/sites/<slug>`). */
export function usePublicMatch(base: string, matchId: string | null) {
  return useQuery({
    queryKey: ["public-match", base, matchId],
    queryFn: () => apiGet(`${base}/match/${encodeURIComponent(matchId!)}`, matchSchema),
    enabled: matchId !== null,
    refetchInterval: poll,
  });
}

export function useStartPublicMatch(base: string) {
  return useMutation({
    mutationFn: (body: { job_description: string; turnstile_token?: string | null }) =>
      apiSend("POST", `${base}/match`, matchSchema, body),
  });
}

/** Candidate self-check. */
export function useMatch(matchId: string | null) {
  return useQuery({
    queryKey: ["matches", matchId],
    queryFn: () => apiGet(`/matches/${encodeURIComponent(matchId!)}`, matchSchema),
    enabled: matchId !== null,
    refetchInterval: poll,
  });
}

export function useStartMatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (job_description: string) => apiSend("POST", "/matches", matchSchema, { job_description }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["matches", "list"] }),
  });
}

export function useMatchHistory(page = 1) {
  return useQuery({
    queryKey: ["matches", "list", page],
    queryFn: () => apiGet(`/matches${page > 1 ? `?page=${page}` : ""}`, matchListSchema),
  });
}
