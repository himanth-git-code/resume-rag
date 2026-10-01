"use client";

import { useState } from "react";

import { Turnstile } from "@/components/public-profile/turnstile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { chatErrorMessage, usePublicChat } from "@/lib/api/chat";
import { cn } from "@/lib/utils";
import { MAX_QUESTION_CHARS, sourcesLine } from "@/lib/validation/chat";

const SUGGESTIONS = ["What is their most recent role?", "Which databases have they used?", "Have they led a team?"];

export function ChatPanel({ token, name, turnstileSiteKey }: { token: string; name: string; turnstileSiteKey: string | null }) {
  const { sessionId, transcript, send, reset } = usePublicChat(token);
  const [draft, setDraft] = useState("");
  const [botToken, setBotToken] = useState<string | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  const messages = transcript.data?.messages ?? [];
  const pending = messages.some((m) => m.status === "pending");
  const needsCheck = !!turnstileSiteKey && sessionId === null;
  const canSend = draft.trim().length > 0 && !pending && !send.isPending && (!needsCheck || !!botToken);

  async function submit(text: string) {
    const message = text.trim();
    if (!message) return;
    setError(null);
    try {
      await send.mutateAsync({ message, turnstile_token: needsCheck ? botToken : undefined });
      setDraft("");
      // Turnstile tokens are single-use; a later new conversation needs a fresh one.
      if (needsCheck) setBotToken(null);
    } catch (err) {
      const parsed = chatErrorMessage(err);
      setError(parsed);
      if (parsed.code === "no_session" || parsed.code === "session_limit") reset();
      if (parsed.code === "bot_check") setBotToken(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask about {name}</CardTitle>
        <CardDescription>
          Answers come only from the profile information {name} chose to share. If something isn&apos;t covered, the
          assistant will say so.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {messages.length > 0 && (
          <ol className="grid max-h-[28rem] gap-3 overflow-y-auto" aria-live="polite">
            {messages.map((m) => (
              <li key={m.id} className={cn("grid gap-1", m.role === "user" && "justify-items-end")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
                    m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
                  )}
                >
                  {m.status === "pending" && <span className="text-muted-foreground">Thinking…</span>}
                  {m.status === "failed" && (
                    <span className="text-destructive">Couldn&apos;t answer just now. Please ask again.</span>
                  )}
                  {m.status === "done" && m.content}
                </div>
                {m.role === "assistant" && m.status === "done" && sourcesLine(m.citations) && (
                  <p className="max-w-[85%] text-xs text-muted-foreground">{sourcesLine(m.citations)}</p>
                )}
              </li>
            ))}
          </ol>
        )}

        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <Button key={s} size="sm" variant="outline" disabled={needsCheck && !botToken} onClick={() => submit(s)}>
                {s}
              </Button>
            ))}
          </div>
        )}

        <form
          className="grid gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (canSend) void submit(draft);
          }}
        >
          <Textarea
            aria-label="Your question"
            rows={2}
            maxLength={MAX_QUESTION_CHARS}
            placeholder="e.g. Does the candidate have AWS experience?"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (canSend) void submit(draft);
              }
            }}
          />
          {needsCheck && <Turnstile siteKey={turnstileSiteKey!} onToken={setBotToken} />}
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {draft.length}/{MAX_QUESTION_CHARS}
            </span>
            <div className="flex gap-2">
              {sessionId && (
                <Button type="button" variant="ghost" size="sm" onClick={reset}>
                  New conversation
                </Button>
              )}
              <Button type="submit" size="sm" disabled={!canSend}>
                {send.isPending ? "Sending…" : "Ask"}
              </Button>
            </div>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error.message}
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
