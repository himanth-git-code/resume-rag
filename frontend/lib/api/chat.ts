import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import {
  chatErrorSchema,
  chatSessionDetailSchema,
  chatSessionListSchema,
  chatTranscriptSchema,
} from "@/lib/validation/chat";

const storageKey = (base: string) => `chat-session:${base}`;

function readSession(base: string): string | null {
  try {
    return sessionStorage.getItem(storageKey(base));
  } catch {
    return null;
  }
}

function writeSession(base: string, id: string | null) {
  try {
    if (id) sessionStorage.setItem(storageKey(base), id);
    else sessionStorage.removeItem(storageKey(base));
  } catch {
    // Storage unavailable (private mode etc.): the chat still works for this page view.
  }
}

/**
 * Public chat (employer profile `/public/p/<token>` or website `/public/sites/<slug>`):
 * one conversation per browser tab, polled while an answer is pending.
 */
export function usePublicChat(base: string) {
  const queryClient = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : readSession(base),
  );
  const key = ["public-chat", base, sessionId];

  const transcript = useQuery({
    queryKey: key,
    enabled: sessionId !== null,
    queryFn: async () => {
      try {
        return await apiGet(`${base}/chat/${encodeURIComponent(sessionId!)}`, chatTranscriptSchema);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          writeSession(base, null);
          setSessionId(null);
          return null;
        }
        throw error;
      }
    },
    refetchInterval: (q) => (q.state.data?.messages.some((m) => m.status === "pending") ? 1500 : false),
  });

  const send = useMutation({
    mutationFn: (body: { message: string; turnstile_token?: string | null }) =>
      apiSend("POST", `${base}/chat`, chatTranscriptSchema, {
        ...body,
        session_id: sessionId,
      }),
    onSuccess: (data) => {
      writeSession(base, data.session_id);
      if (data.session_id !== sessionId) setSessionId(data.session_id);
      queryClient.setQueryData(["public-chat", base, data.session_id], (old: typeof data | null | undefined) => ({
        session_id: data.session_id,
        messages: [...(old?.messages ?? []), ...data.messages],
      }));
    },
  });

  const reset = useCallback(() => {
    writeSession(base, null);
    setSessionId(null);
  }, [base]);

  return { sessionId, transcript, send, reset };
}

export function chatErrorMessage(error: unknown): { code: string; message: string } {
  if (error instanceof ApiError) {
    const parsed = chatErrorSchema.safeParse(error.body);
    if (parsed.success) return { code: parsed.data.code, message: parsed.data.detail };
    if (error.status === 429) return { code: "throttled", message: "Too many questions for now. Please try again later." };
    if (error.status === 404) return { code: "unavailable", message: "The assistant isn't available on this profile." };
  }
  return { code: "network", message: "Your question couldn't be sent. Please try again." };
}

export function useMyChatSessions(page = 1) {
  return useQuery({
    queryKey: ["employer-profile", "chats", page],
    queryFn: () => apiGet(`/employer-profile/chats${page > 1 ? `?page=${page}` : ""}`, chatSessionListSchema),
  });
}

export function useMyChatSession(id: string | null) {
  return useQuery({
    queryKey: ["employer-profile", "chat", id],
    queryFn: () => apiGet(`/employer-profile/chats/${encodeURIComponent(id!)}`, chatSessionDetailSchema),
    enabled: id !== null,
  });
}
