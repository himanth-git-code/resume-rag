"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { FilePicker } from "@/components/support/reply-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { useMyTickets, useOpenTicket } from "@/lib/api/support";
import { CANDIDATE_PRIORITIES, checkFiles, PRIORITY_LABEL, STATUS_LABEL } from "@/lib/validation/support";

function NewRequest({ onDone }: { onDone: () => void }) {
  const open = useOpenTicket();
  const router = useRouter();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<(typeof CANDIDATE_PRIORITIES)[number]>("normal");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      noValidate
      className="grid gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const problem =
          !subject.trim() ? "Add a subject." : !description.trim() ? "Describe what's happening." : checkFiles(files);
        setError(problem);
        if (problem) return;
        try {
          const ticket = await open.mutateAsync({ subject: subject.trim(), description: description.trim(), priority, files });
          onDone();
          router.push(`/support/${ticket.number}`);
        } catch (err) {
          setError(
            err instanceof ApiError && err.status === 429
              ? "You've opened several requests today. Please reply on an existing one or try tomorrow."
              : ((err instanceof ApiError ? (err.body as { detail?: string } | null)?.detail : null) ??
                  "Your request couldn't be sent. Please try again."),
          );
        }
      }}
    >
      <div className="grid gap-1.5">
        <Label htmlFor="subject">Subject</Label>
        <Input id="subject" maxLength={200} value={subject} onChange={(e) => setSubject(e.target.value)} />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="priority">How urgent is it?</Label>
        <select
          id="priority"
          className="h-9 w-48 rounded-md border border-input bg-transparent px-3 text-sm"
          value={priority}
          onChange={(e) => setPriority(e.target.value as typeof priority)}
        >
          {CANDIDATE_PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {PRIORITY_LABEL[p]}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="description">What&apos;s happening?</Label>
        <Textarea id="description" rows={6} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <FilePicker files={files} setFiles={setFiles} />
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={open.isPending}>
          {open.isPending ? "Sending…" : "Send request"}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export default function SupportPage() {
  const [page, setPage] = useState(1);
  const [composing, setComposing] = useState(false);
  const { data, isPending, isError } = useMyTickets(page);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Support</h1>
          <p className="text-sm text-muted-foreground">Questions or problems? We usually reply within one working day.</p>
        </div>
        {!composing && <Button onClick={() => setComposing(true)}>New request</Button>}
      </div>

      {composing && (
        <Card>
          <CardHeader>
            <CardTitle>New request</CardTitle>
            <CardDescription>Screenshots help: attach PNG, JPEG or PDF files.</CardDescription>
          </CardHeader>
          <CardContent>
            <NewRequest onDone={() => setComposing(false)} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Your requests</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
          {isError && <p className="text-sm text-destructive">Couldn&apos;t load your requests.</p>}
          {data?.results.length === 0 && <p className="text-sm text-muted-foreground">No requests yet.</p>}
          {data?.results.map((t) => (
            <Link
              key={t.number}
              href={`/support/${t.number}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 hover:bg-muted"
            >
              <span className="flex items-center gap-2">
                {t.unread && <span className="size-2 rounded-full bg-primary" aria-label="New reply" />}
                <span className="text-xs text-muted-foreground">{t.number}</span>
                <span className="font-medium">{t.subject}</span>
              </span>
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant={t.status === "waiting_for_user" ? "default" : "outline"}>{STATUS_LABEL[t.status]}</Badge>
                {new Date(t.updated_at).toLocaleDateString()}
              </span>
            </Link>
          ))}
          {(data?.previous || data?.next) && (
            <div className="flex justify-between pt-2">
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
    </div>
  );
}
