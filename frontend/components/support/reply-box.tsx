"use client";

import { Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { checkFiles, MAX_FILES, STAFF_STATUS_LABEL, TICKET_STATUSES } from "@/lib/validation/support";

export type ReplyInput = { body: string; files: File[]; internal: boolean; status?: string };

type Props = {
  onSend: (input: ReplyInput) => Promise<void>;
  pending: boolean;
  staff?: boolean;
  placeholder?: string;
};

export function FilePicker({ files, setFiles }: { files: File[]; setFiles: (files: File[]) => void }) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button type="button" variant="outline" size="sm" disabled={files.length >= MAX_FILES} onClick={() => input.current?.click()}>
        <Paperclip /> Attach
      </Button>
      <input
        ref={input}
        type="file"
        multiple
        accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"
        className="sr-only"
        aria-label="Attach files"
        onChange={(e) => {
          setFiles([...files, ...Array.from(e.target.files ?? [])].slice(0, MAX_FILES + 1));
          e.target.value = "";
        }}
      />
      {files.map((f, i) => (
        <span key={`${f.name}-${i}`} className="flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs">
          {f.name}
          <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}>
            <X className="size-3" />
          </button>
        </span>
      ))}
      <span className="text-xs text-muted-foreground">PNG, JPEG or PDF · up to 3 files, 5 MB each</span>
    </div>
  );
}

export function ReplyBox({ onSend, pending, staff = false, placeholder }: Props) {
  const [body, setBody] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [internal, setInternal] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const problem = !body.trim() ? "Write a message first." : checkFiles(files);
    setError(problem);
    if (problem) return;
    try {
      await onSend({ body: body.trim(), files, internal, status: status || undefined });
      setBody("");
      setFiles([]);
      setStatus("");
    } catch (err) {
      const detail = err instanceof ApiError ? (err.body as { detail?: string } | null)?.detail : null;
      setError(detail || "Your message couldn't be sent. Please try again.");
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3" noValidate>
      <Textarea
        rows={4}
        maxLength={5000}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder ?? "Write a reply…"}
        aria-label="Message"
        className={internal ? "border-amber-400" : undefined}
      />
      <FilePicker files={files} setFiles={setFiles} />
      {staff && (
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch id="internal" checked={internal} onCheckedChange={setInternal} />
            <Label htmlFor="internal">Internal note (not visible to the candidate)</Label>
          </div>
          <select
            aria-label="Set status"
            className="h-8 rounded-md border border-input bg-transparent px-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">{internal ? "Keep status" : "Status: Waiting for user"}</option>
            {TICKET_STATUSES.map((s) => (
              <option key={s} value={s}>
                Status: {STAFF_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div>
        <Button type="submit" disabled={pending}>
          {pending ? "Sending…" : internal ? "Add note" : "Send"}
        </Button>
      </div>
    </form>
  );
}
