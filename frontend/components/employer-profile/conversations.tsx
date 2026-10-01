"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useMyChatSession, useMyChatSessions } from "@/lib/api/chat";
import { sourcesLine } from "@/lib/validation/chat";

function Transcript({ id }: { id: string }) {
  const { data, isPending, isError } = useMyChatSession(id);
  if (isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (isError) return <p className="text-sm text-destructive">Couldn&apos;t load this conversation.</p>;
  return (
    <ol className="grid gap-2 border-l pl-4 text-sm">
      {data.messages.map((m) => (
        <li key={m.id} className="grid gap-0.5">
          <span className="text-xs font-medium text-muted-foreground">{m.role === "user" ? "Employer" : "Assistant"}</span>
          <span className="whitespace-pre-wrap">
            {m.status === "pending" ? "…" : m.status === "failed" ? "(no answer)" : m.content}
          </span>
          {sourcesLine(m.citations) && <span className="text-xs text-muted-foreground">{sourcesLine(m.citations)}</span>}
        </li>
      ))}
    </ol>
  );
}

export function Conversations() {
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<string | null>(null);
  const { data, isPending, isError } = useMyChatSessions(page);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversations</CardTitle>
        <CardDescription>Questions employers asked the assistant, and what it answered.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
        {isError && <p className="text-sm text-destructive">Couldn&apos;t load conversations.</p>}
        {data?.results.length === 0 && <p className="text-sm text-muted-foreground">No conversations yet.</p>}
        {data?.results.map((s) => (
          <div key={s.id} className="grid gap-2 rounded-lg border p-3">
            <button
              type="button"
              className="flex flex-wrap items-baseline justify-between gap-2 text-left"
              aria-expanded={open === s.id}
              onClick={() => setOpen(open === s.id ? null : s.id)}
            >
              <span className="text-sm font-medium">&ldquo;{s.first_question}&rdquo;</span>
              <span className="text-xs text-muted-foreground">
                {s.question_count} question{s.question_count === 1 ? "" : "s"} ·{" "}
                {new Date(s.last_activity).toLocaleString()}
              </span>
            </button>
            {open === s.id && <Transcript id={s.id} />}
          </div>
        ))}
        {(data?.previous || data?.next) && (
          <div className="flex justify-between">
            <Button size="sm" variant="outline" disabled={!data?.previous} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button size="sm" variant="outline" disabled={!data?.next} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
