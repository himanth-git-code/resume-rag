"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { noteInputSchema } from "@/lib/validation/notes";
import type { NoteInput } from "@/types/notes";

type Props = {
  initial?: NoteInput;
  submitLabel: string;
  pending: boolean;
  onSubmit: (input: NoteInput) => Promise<void>;
  onCancel?: () => void;
};

export function NoteEditor({ initial, submitLabel, pending, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [errors, setErrors] = useState<Partial<Record<keyof NoteInput | "form", string>>>({});

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = noteInputSchema.safeParse({ title, body });
    if (!parsed.success) {
      const next: typeof errors = {};
      for (const issue of parsed.error.issues) next[issue.path[0] as keyof NoteInput] ??= issue.message;
      setErrors(next);
      return;
    }
    setErrors({});
    try {
      await onSubmit(parsed.data);
    } catch {
      setErrors({ form: "Your note couldn't be saved. Please try again." });
    }
  }

  return (
    <form onSubmit={submit} noValidate className="grid gap-3">
      <div className="grid gap-1.5">
        <Label htmlFor="note-title">Title</Label>
        <Input
          id="note-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-invalid={Boolean(errors.title)}
        />
        {errors.title && <p className="text-xs text-destructive">{errors.title}</p>}
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="note-body">Note</Label>
        <Textarea
          id="note-body"
          rows={6}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          aria-invalid={Boolean(errors.body)}
        />
        {errors.body && <p className="text-xs text-destructive">{errors.body}</p>}
      </div>
      {errors.form && (
        <p role="alert" className="text-sm text-destructive">
          {errors.form}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
