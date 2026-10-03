"use client";

import Link from "next/link";
import { use } from "react";

import { Conversation } from "@/components/support/conversation";
import { ReplyBox } from "@/components/support/reply-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api/client";
import { useCloseTicket, useMyTicket, useReply } from "@/lib/api/support";
import { STATUS_LABEL } from "@/lib/validation/support";

export default function TicketPage({ params }: { params: Promise<{ number: string }> }) {
  const { number } = use(params);
  const ticket = useMyTicket(number);
  const reply = useReply(number);
  const close = useCloseTicket(number);

  if (ticket.isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (ticket.isError) {
    const missing = ticket.error instanceof ApiError && ticket.error.status === 404;
    return (
      <p role="alert" className="text-sm text-destructive">
        {missing ? "This request doesn't exist." : "Couldn't load this request. Please refresh."}
      </p>
    );
  }

  const t = ticket.data;
  const closed = t.status === "closed";
  return (
    <div className="grid gap-6">
      <div>
        <Link href="/support" className="text-sm text-muted-foreground hover:underline">
          ← All requests
        </Link>
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t.subject}</h1>
          <Badge variant="outline">{STATUS_LABEL[t.status]}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {t.number} · opened {new Date(t.created_at).toLocaleString()}
        </p>
      </div>

      <Card>
        <CardContent>
          <Conversation messages={t.messages} perspective="candidate" />
        </CardContent>
      </Card>

      {closed ? (
        <p className="text-sm text-muted-foreground">
          This request is closed. <Link href="/support" className="underline">Open a new request</Link> if you need more help.
        </p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Reply</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <ReplyBox pending={reply.isPending} onSend={({ body, files }) => reply.mutateAsync({ body, files }).then(() => undefined)} />
            <div>
              <Button
                variant="ghost"
                size="sm"
                disabled={close.isPending}
                onClick={() => window.confirm("Close this request? You can open a new one any time.") && close.mutate()}
              >
                Close request
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
