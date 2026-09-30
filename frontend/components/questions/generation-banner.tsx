"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { isGenerating } from "@/lib/api/questions";
import type { QuestionGeneration } from "@/types/questions";

type Props = {
  generation: QuestionGeneration | null;
  profileChanged: boolean;
  onRegenerate: () => void;
  busy: boolean;
};

export function GenerationBanner({ generation, profileChanged, onRegenerate, busy }: Props) {
  if (generation && isGenerating(generation.status)) {
    const { sections_done: done, sections_total: total } = generation;
    return (
      <Alert aria-live="polite">
        <AlertTitle>{generation.kind === "full" ? "Generating your questions…" : "Generating more questions…"}</AlertTitle>
        <AlertDescription>
          {total > 1 ? `${done} of ${total} sections done. ` : ""}
          This takes a minute or two; questions appear as each part finishes
          {generation.kind === "full" ? " (or all at once when replacing an existing set)" : ""}.
        </AlertDescription>
      </Alert>
    );
  }

  if (generation?.status === "failed") {
    return (
      <Alert variant="destructive">
        <AlertTitle>Question generation didn&apos;t finish</AlertTitle>
        <AlertDescription className="grid gap-3">
          <p>{generation.error_message || "Something went wrong. Please try again."} Your existing questions are unchanged.</p>
          <div>
            <Button size="sm" variant="outline" onClick={onRegenerate} disabled={busy}>
              Try again
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    );
  }

  if (profileChanged) {
    return (
      <Alert>
        <AlertTitle>Your profile has changed</AlertTitle>
        <AlertDescription className="grid gap-3">
          <p>These questions were generated from an earlier version of your profile and notes.</p>
          <div>
            <Button size="sm" onClick={onRegenerate} disabled={busy}>
              Regenerate questions
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    );
  }
  return null;
}
