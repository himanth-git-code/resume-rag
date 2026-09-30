"use client";

import Link from "next/link";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRetryResumeJob } from "@/lib/api/resume";
import type { ParseStatus, ResumeJob } from "@/types/resume";

export const STATUS_LABEL: Record<ParseStatus, string> = {
  pending: "queued",
  parsing: "reading your resume",
  ready_for_review: "ready for review",
  applied: "saved to profile",
  failed: "failed",
};

export function ParseStatusPanel({ job }: { job: ResumeJob }) {
  const retry = useRetryResumeJob();

  return (
    <div className="grid gap-3 text-sm" aria-live="polite">
      <div className="flex items-center justify-between gap-4">
        <span className="truncate text-muted-foreground" title={job.document.original_filename}>
          {job.document.original_filename}
        </span>
        <Badge variant={job.status === "failed" ? "destructive" : "secondary"}>{STATUS_LABEL[job.status]}</Badge>
      </div>

      {(job.status === "pending" || job.status === "parsing") && (
        <p className="text-muted-foreground">
          We&apos;re extracting your experience, skills and education. This usually takes under a minute; you can
          leave this page and come back.
        </p>
      )}

      {job.status === "ready_for_review" && (
        <div className="grid gap-3">
          <p className="text-muted-foreground">
            Your resume has been read. Review and correct the extracted details; nothing is saved to your profile
            until you do.
          </p>
          <div>
            <Button asChild size="sm">
              <Link href="/profile">Review details</Link>
            </Button>
          </div>
        </div>
      )}

      {job.status === "failed" && (
        <Alert variant="destructive">
          <AlertTitle>We couldn&apos;t read this resume</AlertTitle>
          <AlertDescription className="grid gap-3">
            <p>{job.error_message || "Something went wrong. Please try again."}</p>
            <div>
              <Button size="sm" variant="outline" onClick={() => retry.mutate(job.id)} disabled={retry.isPending}>
                {retry.isPending ? "Retrying…" : "Try again"}
              </Button>
            </div>
            {retry.isError && <p>Retry failed. Please try again shortly.</p>}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
