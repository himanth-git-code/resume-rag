"use client";

import Link from "next/link";
import { useState } from "react";

import { ProfileForm } from "@/components/profile/profile-form";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useProfile, useResumeDraft } from "@/lib/api/profile";
import { isInProgress, useLatestResumeJob } from "@/lib/api/resume";
import { toFormValues } from "@/lib/validation/profile";

export default function ProfilePage() {
  const job = useLatestResumeJob();
  const reviewJobId = job.data?.status === "ready_for_review" ? job.data.id : null;
  const draft = useResumeDraft(reviewJobId);
  const profile = useProfile();
  const [saved, setSaved] = useState(false);

  const loading = job.isPending || profile.isPending || (reviewJobId !== null && draft.isPending);
  const failed = job.isError || profile.isError || draft.isError;

  if (loading) return <p className="text-sm text-muted-foreground">Loading your profile…</p>;
  if (failed) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your profile. Please refresh the page.
      </p>
    );
  }

  const reviewing = reviewJobId !== null && draft.data !== undefined;
  const source = reviewing ? draft.data : profile.data;
  // Remount the form when its source changes (e.g. draft saved -> saved profile).
  const formKey = reviewing ? `draft-${reviewJobId}` : `profile-${profile.data?.updated_at ?? "new"}`;

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        <p className="text-sm text-muted-foreground">
          This is the information employers and your website will draw on. Only what you save here is used.
        </p>
      </div>

      {reviewing && (
        <Alert>
          <AlertTitle>Review the details we extracted from your resume</AlertTitle>
          <AlertDescription>
            Check every section and fix anything that&apos;s wrong or missing. Fields left blank weren&apos;t found
            in your resume. Nothing is saved until you press &ldquo;Save to my profile&rdquo;
            {profile.data ? ", which replaces your current profile" : ""}.
          </AlertDescription>
        </Alert>
      )}

      {!reviewing && job.data && isInProgress(job.data.status) && (
        <Alert>
          <AlertDescription>
            Your latest resume is still being read. You can edit your profile now, or wait and review the extracted
            details when they&apos;re ready.
          </AlertDescription>
        </Alert>
      )}

      {!reviewing && !profile.data && !job.data && (
        <Alert>
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            <span>Save time by uploading your resume. We&apos;ll fill this in for you to review.</span>
            <Button asChild size="sm" variant="outline">
              <Link href="/resume">Upload resume</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {saved && !reviewing && (
        <Alert>
          <AlertDescription>Your profile has been saved.</AlertDescription>
        </Alert>
      )}

      <ProfileForm
        key={formKey}
        defaultValues={toFormValues(source ?? null)}
        jobId={reviewing ? reviewJobId : null}
        onSaved={() => {
          setSaved(true);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      />
    </div>
  );
}
