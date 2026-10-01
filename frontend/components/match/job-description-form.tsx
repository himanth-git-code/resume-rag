"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { checkJobDescription, MAX_JD_CHARS } from "@/lib/validation/match";

type Props = {
  onSubmit: (jobDescription: string) => Promise<void>;
  pending: boolean;
  disabled?: boolean;
  /** Extra content above the submit button (e.g. a bot check). */
  children?: React.ReactNode;
};

export function JobDescriptionForm({ onSubmit, pending, disabled, children }: Props) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      noValidate
      className="grid gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const problem = checkJobDescription(text);
        setError(problem);
        if (problem) return;
        try {
          await onSubmit(text.trim());
        } catch (err) {
          setError(err instanceof Error ? err.message : "Something went wrong.");
        }
      }}
    >
      <div className="grid gap-1.5">
        <Label htmlFor="job-description">Job description</Label>
        <Textarea
          id="job-description"
          rows={8}
          maxLength={MAX_JD_CHARS}
          placeholder="Paste the full job description, including its requirements."
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-invalid={Boolean(error)}
        />
        <p className="text-xs text-muted-foreground">
          The job description is used only for this analysis and isn&apos;t saved.
        </p>
      </div>
      {children}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div>
        <Button type="submit" disabled={pending || disabled}>
          {pending ? "Submitting…" : "Analyse match"}
        </Button>
      </div>
    </form>
  );
}
